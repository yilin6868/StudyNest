"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";
import type { Stats } from "@/lib/api/types";

const DEFAULTS = { focus: 25 * 60, break: 5 * 60 };
const TIMER_KEY = "sb_timer";
const EMPTY_STATS: Stats = { date: "", tomato: 0, minutes: 0, streak: 0, weekDays: [] };

const fmt = (s: number) => {
  s = Math.max(0, Math.floor(s));
  return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
};

interface TimerState {
  mode: "focus" | "break";
  remaining: number;
  running: boolean;
  endAt: number;
  halfDone: boolean;
}

function readTimer(): TimerState {
  if (typeof window === "undefined") {
    return { mode: "focus", remaining: DEFAULTS.focus, running: false, endAt: 0, halfDone: false };
  }
  try {
    const s = JSON.parse(localStorage.getItem(TIMER_KEY) || "null");
    if (s) {
      const mode = s.mode === "break" ? "break" : "focus";
      const max = mode === "focus" ? DEFAULTS.focus : DEFAULTS.break;
      if (s.running && s.endAt) {
        const left = Math.round((s.endAt - Date.now()) / 1000);
        if (left > 0) {
          return { mode, remaining: left, running: true, endAt: s.endAt, halfDone: left < DEFAULTS.focus / 2 };
        }
      }
      const rem = Math.min(s.remaining || max, max);
      return { mode, remaining: rem, running: false, endAt: 0, halfDone: rem < DEFAULTS.focus / 2 };
    }
  } catch {
    /* 忽略 */
  }
  return { mode: "focus", remaining: DEFAULTS.focus, running: false, endAt: 0, halfDone: false };
}

export default function FocusPage() {
  const [timer, setTimer] = useState<TimerState>(readTimer);
  const [stats, setStats] = useState<Stats>(EMPTY_STATS);
  const [bubble, setBubble] = useState("点「开始」，搭子陪你一起专注 🍅");
  const [typing, setTyping] = useState(false);
  const [buddy] = useState(() => {
    if (typeof window === "undefined") {
      return { src: "/assets/buddy-male.jpg", gender: "male" as const };
    }
    const b = localStorage.getItem("sb_buddy");
    return b === "female"
      ? { src: "/assets/buddy-female.jpg", gender: "female" as const }
      : { src: "/assets/buddy-male.jpg", gender: "male" as const };
  });

  const timerRef = useRef(timer);
  const bubbleTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    timerRef.current = timer;
  }, [timer]);

  // ==================== 统计 ====================
  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch(() => setStats(EMPTY_STATS));
  }, []);

  // ==================== 搭子说话（气泡 + 语音） ====================
  function focusSpeak(text: string) {
    if (bubbleTimerRef.current) clearInterval(bubbleTimerRef.current);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setTyping(true);
    let i = 0;
    const step = Math.max(1, Math.round(text.length / 40));
    setBubble("");
    bubbleTimerRef.current = setInterval(() => {
      i += step;
      setBubble(text.slice(0, i));
      if (i >= text.length) {
        if (bubbleTimerRef.current) clearInterval(bubbleTimerRef.current);
        bubbleTimerRef.current = null;
        setTyping(false);
      }
    }, 30);

    api.tts(text, buddy.gender).then((url) => {
      if (!url) return;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        URL.revokeObjectURL(url);
        if (audioRef.current === audio) audioRef.current = null;
      };
      audio.play().catch(() => URL.revokeObjectURL(url));
    });
  }

  async function sceneSpeak(scene: Parameters<typeof api.encourage>[0]) {
    try {
      const d = await api.encourage(scene);
      if (d.reply) focusSpeak(d.reply);
    } catch {
      /* 忽略 */
    }
  }

  // ==================== 番茄钟操作 ====================
  function persist(t: TimerState) {
    localStorage.setItem(
      TIMER_KEY,
      JSON.stringify({ mode: t.mode, remaining: Math.max(0, Math.round(t.remaining)), endAt: t.endAt, running: t.running }),
    );
  }

  function switchMode(m: "focus" | "break") {
    const next: TimerState = {
      mode: m,
      remaining: m === "focus" ? DEFAULTS.focus : DEFAULTS.break,
      running: false,
      endAt: 0,
      halfDone: false,
    };
    setTimer(next);
    persist(next);
  }

  function toggleTimer() {
    const t = timerRef.current;
    if (t.running) {
      const left = t.endAt ? Math.max(0, Math.round((t.endAt - Date.now()) / 1000)) : t.remaining;
      const next: TimerState = { ...t, running: false, remaining: left, endAt: 0 };
      setTimer(next);
      persist(next);
      return;
    }
    const next: TimerState = {
      ...t,
      running: true,
      endAt: Date.now() + t.remaining * 1000,
      halfDone: t.remaining < DEFAULTS.focus / 2,
    };
    setTimer(next);
    persist(next);
    if (t.mode === "focus" && t.remaining >= DEFAULTS.focus) sceneSpeak("start");
    else if (t.mode === "break" && t.remaining >= DEFAULTS.break) sceneSpeak("break");
  }

  function resetTimer() {
    switchMode(timerRef.current.mode);
  }

  async function finish() {
    const t = timerRef.current;
    setTimer((p) => ({ ...p, running: false, remaining: 0, endAt: 0 }));
    if (t.mode === "focus") {
      try {
        const s = await api.completeTomato(25);
        setStats(s);
      } catch {
        setStats((p) => ({ ...p, tomato: (p.tomato || 0) + 1 }));
      }
      sceneSpeak("celebrate");
      switchMode("break");
    } else {
      sceneSpeak("breakOver");
      switchMode("focus");
    }
  }

  // ==================== 计时循环 ====================
  useEffect(() => {
    if (!timer.running) return;
    const iv = setInterval(() => {
      const t = timerRef.current;
      const left = Math.round((t.endAt - Date.now()) / 1000);
      if (left <= 0) {
        setTimer((p) => ({ ...p, remaining: 0 }));
        finish();
      } else {
        setTimer((p) => ({ ...p, remaining: left }));
        if (t.mode === "focus" && !t.halfDone && left <= DEFAULTS.focus / 2) {
          setTimer((p) => ({ ...p, halfDone: true }));
          sceneSpeak("encourage");
        }
      }
    }, 1000);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timer.running]);

  // 卸载清理
  useEffect(() => {
    return () => {
      if (bubbleTimerRef.current) clearInterval(bubbleTimerRef.current);
      if (audioRef.current) audioRef.current.pause();
    };
  }, []);

  const isBreak = timer.mode === "break";
  const startLabel = timer.running
    ? "暂停"
    : isBreak
      ? "开始休息"
      : timer.remaining < DEFAULTS.focus
        ? "继续专注"
        : "开始专注";

  return (
    <div className="flex h-full flex-col gap-3.5 p-3.5 pb-2">
      {/* 搭子头 */}
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
            {timer.running ? "陪你专注中…" : "陪你一起专注"}
          </div>
        </div>
      </div>

      {/* 气泡 */}
      <div className="min-h-[48px] rounded-[16px] rounded-bl-[4px] border border-line bg-surface px-3.5 py-3 text-[15px] leading-relaxed">
        {bubble}
        {typing && <span className="text-accent">▍</span>}
      </div>

      {/* 计时器 */}
      <div className="rounded-[20px] border border-line bg-surface px-4 py-5 text-center">
        <div className="mb-4 flex gap-1.5 rounded-xl bg-black/22 p-1">
          <button
            type="button"
            onClick={() => switchMode("focus")}
            className={`flex-1 rounded-[9px] py-2 text-[13px] font-semibold transition-colors ${
              !isBreak ? "bg-linear-to-br from-accent to-accent-2 text-[#241a0e]" : "text-muted"
            }`}
          >
            专注
          </button>
          <button
            type="button"
            onClick={() => switchMode("break")}
            className={`flex-1 rounded-[9px] py-2 text-[13px] font-semibold transition-colors ${
              isBreak ? "bg-linear-to-br from-accent to-accent-2 text-[#241a0e]" : "text-muted"
            }`}
          >
            休息
          </button>
        </div>

        <div
          className={`my-1.5 text-[64px] font-extrabold leading-none tracking-wide tabular-nums ${
            timer.running ? "text-accent drop-shadow-[0_0_26px_rgba(255,180,84,0.35)]" : ""
          }`}
        >
          {fmt(timer.remaining)}
        </div>
        <div className="mb-4 min-h-4 text-xs text-muted">
          {timer.running
            ? ""
            : isBreak
              ? "休息是为了更好地出发 🌿"
              : "点「开始」，搭子陪你一起专注"}
        </div>

        <div className="flex justify-center gap-2.5">
          <button
            type="button"
            onClick={toggleTimer}
            className="max-w-[220px] flex-1 rounded-[13px] bg-linear-to-br from-accent to-accent-2 px-5 py-3 text-sm font-bold text-[#241a0e] shadow-[0_6px_18px_rgba(255,160,80,0.35)] active:scale-95"
          >
            {startLabel}
          </button>
          <button
            type="button"
            onClick={resetTimer}
            className="rounded-[13px] border border-line bg-white/8 px-5 py-3 text-sm text-foreground"
          >
            重置
          </button>
        </div>
      </div>

      {/* 统计 */}
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
