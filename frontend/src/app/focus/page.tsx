"use client";

import { useEffect, useRef, useState } from "react";
import TodayGoalCard from "@/components/TodayGoalCard";
import { useVoice } from "@/components/providers/VoiceProvider";
import { api } from "@/lib/api/client";
import type { Stats } from "@/lib/api/types";
import { useStoredString } from "@/lib/browser-storage";
import {
  createSessionId,
  DEFAULT_SECONDS,
  idleTimer,
  restoreTimer,
  TIMER_KEY,
  type TimerMode,
  type TimerState,
} from "@/lib/timer";

const EMPTY_STATS: Stats = { date: "", tomato: 0, minutes: 0, streak: 0, weekDays: [] };

const fmt = (seconds: number) => {
  const safe = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(safe / 60)).padStart(2, "0")}:${String(safe % 60).padStart(2, "0")}`;
};

export default function FocusPage() {
  const [timer, setTimer] = useState<TimerState>(() => idleTimer());
  const [timerReady, setTimerReady] = useState(false);
  const [stats, setStats] = useState<Stats>(EMPTY_STATS);
  const [bubble, setBubble] = useState("点「开始」，搭子陪你一起专注 🍅");
  const [typing, setTyping] = useState(false);
  const [notice, setNotice] = useState("");
  const [midSessionEncouragement, setMidSessionEncouragement] = useState(false);
  const [focusOptions, setFocusOptions] = useState<number[]>([25]);
  const [customFocusEnabled, setCustomFocusEnabled] = useState(false);
  const [selectedMinutes, setSelectedMinutes] = useState(25);
  const storedBuddy = useStoredString("sb_buddy", "male");
  const buddy =
    storedBuddy === "female"
      ? { src: "/assets/buddy-female.jpg", gender: "female" as const }
      : { src: "/assets/buddy-male.jpg", gender: "male" as const };
  const { speak: playVoice, stop: stopVoice } = useVoice();

  const timerRef = useRef(timer);
  const bubbleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const settlingRef = useRef<string | null>(null);

  useEffect(() => {
    timerRef.current = timer;
  }, [timer]);

  useEffect(() => {
    const task = window.setTimeout(() => {
      const restored = restoreTimer(localStorage.getItem(TIMER_KEY));
      if (restored.discardedLegacyState) {
        localStorage.removeItem(TIMER_KEY);
        setNotice("旧计时记录无法安全确认，已重置，请重新开始。");
      }
      timerRef.current = restored.timer;
      setTimer(restored.timer);
      setTimerReady(true);
    }, 0);
    return () => window.clearTimeout(task);
  }, []);

  useEffect(() => {
    if (timerReady) localStorage.setItem(TIMER_KEY, JSON.stringify(timer));
  }, [timer, timerReady]);

  useEffect(() => {
    api.getStats().then(setStats).catch(() => setStats(EMPTY_STATS));
    api.getCompanionPreferences().then((value) => { setMidSessionEncouragement(value.mid_session_encouragement_enabled); setCustomFocusEnabled(value.custom_focus_enabled); setSelectedMinutes(value.default_focus_minutes); }).catch(() => undefined);
    api.getFocusOptions().then((value) => { setFocusOptions(value.options); setCustomFocusEnabled(value.enabled); setSelectedMinutes(value.default_minutes); }).catch(() => undefined);
  }, []);

  function focusSpeak(text: string) {
    if (bubbleTimerRef.current) clearInterval(bubbleTimerRef.current);
    setTyping(true);
    let index = 0;
    const step = Math.max(1, Math.round(text.length / 40));
    setBubble("");
    bubbleTimerRef.current = setInterval(() => {
      index += step;
      setBubble(text.slice(0, index));
      if (index >= text.length) {
        if (bubbleTimerRef.current) clearInterval(bubbleTimerRef.current);
        bubbleTimerRef.current = null;
        setTyping(false);
      }
    }, 30);
    void playVoice(text, buddy.gender);
  }

  async function sceneSpeak(scene: Parameters<typeof api.encourage>[0]) {
    try {
      const response = await api.encourage(scene);
      if (response.reply) focusSpeak(response.reply);
    } catch {
      // 鼓励话术失败不影响计时和结算。
    }
  }

  function switchMode(mode: TimerMode) {
    stopVoice();
    setNotice("");
    setTimer(idleTimer(mode));
  }

  function toggleTimer() {
    const current = timerRef.current;
    if (!timerReady || ["pending_settlement", "settlement_failed"].includes(current.status)) {
      return;
    }

    if (current.status === "running") {
      const remaining = current.endAt
        ? Math.max(0, Math.ceil((current.endAt - Date.now()) / 1000))
        : current.remainingSeconds;
      setTimer({
        ...current,
        status: "paused",
        endAt: null,
        remainingSeconds: remaining,
      });
      return;
    }

    const now = Date.now();
    const isNewFocus = current.mode === "focus" && !current.sessionId;
    const next: TimerState = {
      ...current,
      sessionId:
        current.mode === "focus" ? current.sessionId ?? createSessionId() : null,
      status: "running",
      startedAt: isNewFocus || !current.startedAt ? now : current.startedAt,
      endAt: now + current.remainingSeconds * 1000,
      halfDone: current.remainingSeconds <= current.durationSeconds / 2,
    };
    setNotice("");
    setTimer(next);
    if (current.mode === "focus" && current.remainingSeconds >= current.durationSeconds) {
      void api.recordProductEvent("focus.started", next.sessionId ?? undefined, Math.round(next.durationSeconds / 60));
      void sceneSpeak("start");
    } else if (current.mode === "break" && current.remainingSeconds >= DEFAULT_SECONDS.break) {
      void sceneSpeak("break");
    }
  }

  useEffect(() => {
    if (!timerReady || timer.status !== "running" || !timer.endAt) return;

    const interval = setInterval(() => {
      const current = timerRef.current;
      if (current.status !== "running" || !current.endAt) return;
      const remaining = Math.ceil((current.endAt - Date.now()) / 1000);
      if (remaining <= 0) {
        if (current.mode === "focus") {
          setTimer({ ...current, status: "pending_settlement", remainingSeconds: 0, endAt: null });
        } else {
          setTimer(idleTimer("focus"));
          void sceneSpeak("breakOver");
        }
        return;
      }

      const crossedHalf =
        current.mode === "focus" &&
        !current.halfDone &&
        remaining <= current.durationSeconds / 2;
      setTimer({
        ...current,
        remainingSeconds: remaining,
        halfDone: current.halfDone || crossedHalf,
      });
      if (crossedHalf) void api.recordProductEvent("focus.halfway_shown", current.sessionId ?? undefined);
      if (crossedHalf && midSessionEncouragement) void sceneSpeak("encourage");
    }, 1000);

    return () => clearInterval(interval);
    // sceneSpeak uses the current page state and must not restart the timer interval.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timer.status, timer.endAt, timerReady, midSessionEncouragement]);

  useEffect(() => {
    if (!timerReady || timer.status !== "pending_settlement" || !timer.sessionId) return;
    if (settlingRef.current === timer.sessionId) return;

    const sessionId = timer.sessionId;
    settlingRef.current = sessionId;
    setNotice("正在保存本次专注…");
    const minutes = Math.max(1, Math.round(timerRef.current.durationSeconds / 60));
    api
      .completeTomato(sessionId, minutes)
      .then(async (nextStats) => {
        void api.recordProductEvent("focus.completed", sessionId, minutes);
        setStats(nextStats);
        setNotice("本次专注已保存。");
        setTimer(idleTimer("break"));
        try {
          const summary = await api.focusSummary(sessionId);
          focusSpeak(summary.reply);
        } catch {
          void sceneSpeak("celebrate");
        }
      })
      .catch(() => {
        void api.recordProductEvent("focus.completion_failed", sessionId, minutes);
        setNotice("本次专注保存失败，请重新保存。");
        setTimer((current) => ({ ...current, status: "settlement_failed" }));
      })
      .finally(() => {
        settlingRef.current = null;
      });
    // sceneSpeak intentionally does not participate in settlement identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timer.status, timer.sessionId, timerReady]);

  useEffect(() => {
    return () => {
      if (bubbleTimerRef.current) clearInterval(bubbleTimerRef.current);
      stopVoice();
    };
  }, [stopVoice]);

  const isBreak = timer.mode === "break";
  const isRunning = timer.status === "running";
  const isSettling = timer.status === "pending_settlement";
  const settlementFailed = timer.status === "settlement_failed";
  const startLabel = isRunning
    ? "暂停"
    : isBreak
      ? "开始休息"
      : timer.status === "paused"
        ? "继续专注"
        : "开始专注";

  return (
    <div className="flex h-full flex-col gap-3.5 p-3.5 pb-2">
      <div className="flex items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={buddy.src}
          alt="搭子"
          className="h-[52px] w-[52px] rounded-full border-2 border-white/16 object-cover object-[center_35%]"
        />
        <div>
          <div className="text-[15px] font-bold">小悟</div>
          <div className="mt-0.5 text-[11px] text-muted">
            {isRunning ? "陪你专注中…" : "陪你一起专注"}
          </div>
        </div>
      </div>

      <div className="min-h-[48px] rounded-[16px] rounded-bl-[4px] border border-line bg-surface px-3.5 py-3 text-[15px] leading-relaxed">
        {bubble}
        {typing && <span className="text-accent">▍</span>}
      </div>

      <TodayGoalCard readOnly />

      {customFocusEnabled && timer.status === "idle" && timer.mode === "focus" && <div className="flex gap-2 overflow-x-auto">{focusOptions.map((minutes) => <button type="button" key={minutes} onClick={() => { setSelectedMinutes(minutes); setTimer(idleTimer("focus", minutes)); }} className={`rounded-full border px-3 py-1 text-xs ${selectedMinutes === minutes ? "border-accent text-accent" : "border-line text-muted"}`}>{minutes} 分钟</button>)}</div>}

      <div className="rounded-[20px] border border-line bg-surface px-4 py-5 text-center">
        <div className="mb-4 flex gap-1.5 rounded-xl bg-black/22 p-1">
          <button
            type="button"
            onClick={() => switchMode("focus")}
            disabled={isSettling || settlementFailed}
            className={`flex-1 rounded-[9px] py-2 text-[13px] font-semibold transition-colors ${
              !isBreak ? "bg-linear-to-br from-accent to-accent-2 text-[#241a0e]" : "text-muted"
            } disabled:opacity-40`}
          >
            专注
          </button>
          <button
            type="button"
            onClick={() => switchMode("break")}
            disabled={isSettling || settlementFailed}
            className={`flex-1 rounded-[9px] py-2 text-[13px] font-semibold transition-colors ${
              isBreak ? "bg-linear-to-br from-accent to-accent-2 text-[#241a0e]" : "text-muted"
            } disabled:opacity-40`}
          >
            休息
          </button>
        </div>

        <div
          className={`my-1.5 text-[64px] font-extrabold leading-none tracking-wide tabular-nums ${
            isRunning ? "text-accent drop-shadow-[0_0_26px_rgba(255,180,84,0.35)]" : ""
          }`}
        >
          {fmt(timer.remainingSeconds)}
        </div>
        <div className="mb-4 min-h-5 text-xs text-muted" aria-live="polite">
          {notice ||
            (isRunning
              ? ""
              : isBreak
                ? "休息是为了更好地出发 🌿"
                : "点「开始」，搭子陪你一起专注")}
        </div>

        {settlementFailed ? (
          <button
            type="button"
            onClick={() => setTimer((current) => ({ ...current, status: "pending_settlement" }))}
            className="rounded-[13px] bg-linear-to-br from-danger to-accent-2 px-6 py-3 text-sm font-bold text-white"
          >
            重新保存
          </button>
        ) : (
          <div className="flex justify-center gap-2.5">
            <button
              type="button"
              onClick={toggleTimer}
              disabled={!timerReady || isSettling}
              className="max-w-[220px] flex-1 rounded-[13px] bg-linear-to-br from-accent to-accent-2 px-5 py-3 text-sm font-bold text-[#241a0e] shadow-[0_6px_18px_rgba(255,160,80,0.35)] active:scale-95 disabled:opacity-40"
            >
              {isSettling ? "保存中…" : startLabel}
            </button>
            <button
              type="button"
              onClick={() => switchMode(timer.mode)}
              disabled={!timerReady || isSettling}
              className="rounded-[13px] border border-line bg-white/8 px-5 py-3 text-sm text-foreground disabled:opacity-40"
            >
              重置
            </button>
          </div>
        )}
      </div>

      <div className="flex justify-center gap-2">
        <div className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3.5 py-2 text-[13px] text-muted">
          🔥 <b className="text-foreground">{stats.streak || 0}</b>天
        </div>
        <div className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3.5 py-2 text-[13px] text-muted">
          🍅 <b className="text-foreground">{stats.tomato || 0}</b>
        </div>
        <div className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3.5 py-2 text-[13px] text-muted">
          📅 <b className="text-foreground">{(stats.weekDays || []).length || 0}</b>天
        </div>
      </div>
    </div>
  );
}
