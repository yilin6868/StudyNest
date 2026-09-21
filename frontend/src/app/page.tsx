"use client";

import { useEffect, useRef, useState } from "react";
import AgentActionCard from "@/components/AgentActionCard";
import ConversationSwitcher from "@/components/ConversationSwitcher";
import SafetyMessage from "@/components/SafetyMessage";
import TodayGoalCard from "@/components/TodayGoalCard";
import { useVoice } from "@/components/providers/VoiceProvider";
import { api } from "@/lib/api/client";
import type { AgentAction, ConversationSummary } from "@/lib/api/types";
import { getFocusSnapshot } from "@/lib/agent-actions";
import {
  clearStoredChatSession,
  getStoredChatSession,
  storeChatSession,
} from "@/lib/chat-session";
import { setStoredString, useStoredString } from "@/lib/browser-storage";

type Buddy = "male" | "female";

const BUDDIES: Record<Buddy, { src: string; gender: "male" | "female" }> = {
  male: { src: "/assets/buddy-male.jpg", gender: "male" },
  female: { src: "/assets/buddy-female.jpg", gender: "female" },
};

const QUICK_REPLIES = [
  { q: "我有点累了，陪我聊会儿", label: "🥱 我有点累" },
  { q: "最近学习压力好大", label: "😣 压力大" },
  { q: "陪我唠唠日常吧", label: "💬 陪我唠唠" },
  { q: "学不进去，好烦", label: "😮‍💨 学不进去" },
];

interface Msg {
  role: "user" | "buddy";
  text: string;
  actions?: AgentAction[];
  safety?: boolean;
}

export default function ChatPage() {
  const storedBuddy = useStoredString("sb_buddy", "male");
  const buddy: Buddy = storedBuddy === "female" ? "female" : "male";
  const [messages, setMessages] = useState<Msg[]>([]);
  const [subtitle, setSubtitle] = useState("……");
  const [typing, setTyping] = useState(false);
  const [talking, setTalking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [micSupported, setMicSupported] = useState(false);
  const [micMessage, setMicMessage] = useState("");
  const [goalRefreshKey, setGoalRefreshKey] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ConversationSummary[]>([]);
  const {
    voiceEnabled,
    setVoiceEnabled,
    speak: playVoice,
    stop: stopVoice,
  } = useVoice();

  const typeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const listeningRef = useRef(false);
  const finalTranscriptRef = useRef("");
  const chatRef = useRef<HTMLDivElement>(null);

  // ==================== 说话 ====================
  function stopSpeech() {
    stopVoice();
    if (typeTimerRef.current) {
      clearInterval(typeTimerRef.current);
      typeTimerRef.current = null;
    }
    setTyping(false);
    setTalking(false);
  }

  function speak(text: string, actions: AgentAction[] = [], safety = false) {
    stopSpeech();

    // 字幕打字机
    setTyping(true);
    setTalking(true);
    let i = 0;
    const step = Math.max(1, Math.round(text.length / 40));
    setSubtitle("");
    typeTimerRef.current = setInterval(() => {
      i += step;
      setSubtitle(text.slice(0, i));
      if (i >= text.length) {
        if (typeTimerRef.current) clearInterval(typeTimerRef.current);
        typeTimerRef.current = null;
        setTyping(false);
        setTalking(false);
        setMessages((m) => [...m, { role: "buddy", text, actions, safety }]);
      }
    }, 30);

    void playVoice(text, BUDDIES[buddy].gender);
  }

  async function userSay(text: string) {
    if (!text.trim() || busy) return;
    stopSpeech();
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const d = await api.chat(text, getFocusSnapshot(), sessionId);
      setSessionId(d.sessionId);
      storeChatSession(d.sessionId);
      speak(d.reply, d.actions, d.responseMode === "safety");
      void refreshSessions();
      setGoalRefreshKey((value) => value + 1);
    } catch {
      speak("哎呀，我这边信号不太好，稍等再试");
    } finally {
      setBusy(false);
    }
  }

  // ==================== 初始化 ====================
  const speakRef = useRef<((text: string) => void) | null>(null);

  async function refreshSessions() {
    const result = await api.listChatSessions();
    setSessions(result.sessions);
  }

  async function restoreSession(nextSessionId: string) {
    stopSpeech();
    setBusy(true);
    try {
      const result = await api.getChatMessages(nextSessionId);
      let safetyNext = false;
      const restored: Msg[] = [];
      for (const item of result.messages) {
        if (item.role === "safety_marker") {
          if (item.content.includes("原文未保存")) {
            restored.push({ role: "user", text: "[安全消息原文未保存]" });
          }
          safetyNext = true;
        } else if (item.role === "user") {
          restored.push({ role: "user", text: item.content });
          safetyNext = false;
        } else {
          restored.push({ role: "buddy", text: item.content, safety: safetyNext });
          safetyNext = false;
        }
      }
      setMessages(restored);
      setSubtitle(restored.at(-1)?.text ?? "新对话已准备好。");
      setSessionId(nextSessionId);
      storeChatSession(nextSessionId);
    } catch {
      clearStoredChatSession();
      setSessionId(null);
      setMessages([]);
      setSubtitle("这个对话无法恢复，可以开始新对话。");
    } finally {
      setBusy(false);
    }
  }

  async function newConversation() {
    if (busy) return;
    setBusy(true);
    stopSpeech();
    try {
      const result = await api.createChatSession();
      setSessionId(result.sessionId);
      storeChatSession(result.sessionId);
      setMessages([]);
      setSubtitle("新对话已准备好。");
      await refreshSessions();
    } catch {
      setSubtitle("新对话创建失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  async function deleteConversation(targetId: string) {
    if (busy || !window.confirm("确定删除这个对话吗？删除后不能恢复。")) return;
    setBusy(true);
    try {
      await api.deleteChatSession(targetId);
      if (targetId === sessionId) {
        clearStoredChatSession();
        setSessionId(null);
        setMessages([]);
        setSubtitle("对话已删除，可以开始新对话。");
      }
      await refreshSessions();
    } catch {
      setSubtitle("删除失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  // 每次渲染后把最新 speak 写入 ref（供异步回调和空依赖 effect 使用）
  useEffect(() => {
    speakRef.current = speak;
  });

  useEffect(() => {
    const stored = getStoredChatSession();
    void refreshSessions().catch(() => setSessions([]));
    if (stored) {
      window.setTimeout(() => void restoreSession(stored), 0);
    } else {
      api
        .encourage("greet")
        .then((d) => speakRef.current?.(d.reply))
        .catch(() => speakRef.current?.("来啦？今天状态怎么样？"));
    }
    // 初始化只执行一次，会话切换由明确操作驱动。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 卸载清理
  useEffect(() => {
    return () => {
      listeningRef.current = false;
      try {
        recognitionRef.current?.stop();
      } catch {
        // 语音识别可能尚未启动。
      }
      if (typeTimerRef.current) clearInterval(typeTimerRef.current);
      stopVoice();
    };
  }, [stopVoice]);

  function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    userSay(text);
  }

  // 滚动到底部
  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  // ==================== 形象 / 语音开关 ====================
  function switchBuddy(b: Buddy) {
    setStoredString("sb_buddy", b);
  }

  function toggleVoice() {
    const next = !voiceEnabled;
    setVoiceEnabled(next);
    if (!next) stopSpeech();
  }

  // ==================== 语音输入 ====================
  useEffect(() => {
    const SR =
      window.SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionConstructor })
        .webkitSpeechRecognition;
    if (!SR) {
      const task = window.setTimeout(() => {
        setMicSupported(false);
        setMicMessage("当前浏览器不支持语音输入，请使用文字输入。");
      }, 0);
      return () => window.clearTimeout(task);
    }

    const task = window.setTimeout(() => {
      setMicSupported(true);
      setMicMessage("");
    }, 0);

    const rec = new SR();
    rec.lang = "zh-CN";
    rec.interimResults = true;
    rec.continuous = true;

    rec.onresult = (e: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalTranscriptRef.current += t;
        else interim += t;
      }
      setInput(finalTranscriptRef.current + interim);
    };

    rec.onend = () => {
      if (listeningRef.current) {
        try {
          rec.start();
        } catch {
          /* 已在运行 */
        }
      } else {
        setListening(false);
        const text = finalTranscriptRef.current.trim();
        finalTranscriptRef.current = "";
        if (text) {
          setInput("");
          userSay(text);
        }
      }
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        listeningRef.current = false;
        setListening(false);
        setMicMessage("麦克风权限未开启，可以继续打字。");
      } else if (listeningRef.current) {
        setTimeout(() => {
          if (listeningRef.current) {
            try {
              rec.start();
            } catch {
              /* 忽略 */
            }
          }
        }, 300);
      }
    };

    recognitionRef.current = rec;
    return () => window.clearTimeout(task);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startListening() {
    const rec = recognitionRef.current;
    if (!rec || listeningRef.current || !voiceEnabled) return;
    listeningRef.current = true;
    setListening(true);
    finalTranscriptRef.current = "";
    try {
      rec.start();
    } catch {
      /* 忽略 */
    }
  }

  function stopListening() {
    const rec = recognitionRef.current;
    if (!rec) return;
    listeningRef.current = false;
    setListening(false);
    try {
      rec.stop();
    } catch {
      /* 忽略 */
    }
  }

  return (
    <div className="flex h-full flex-col gap-3 p-3 pb-2">
      {/* 语音开关 */}
      <div className="flex items-center justify-between px-1">
        <span className="text-sm text-muted">语音</span>
        <button
          type="button"
          role="switch"
          aria-checked={voiceEnabled}
          onClick={toggleVoice}
          className={`relative h-[26px] w-[46px] rounded-full transition-colors ${
            voiceEnabled
              ? "bg-linear-to-br from-accent to-accent-2"
              : "bg-white/12"
          }`}
        >
          <span
            className={`absolute top-[3px] h-5 w-5 rounded-full bg-white shadow transition-all ${
              voiceEnabled ? "left-[23px]" : "left-[3px]"
            }`}
          />
        </button>
      </div>

      <TodayGoalCard refreshKey={goalRefreshKey} />

      <ConversationSwitcher
        sessions={sessions}
        currentId={sessionId}
        busy={busy}
        onNew={() => void newConversation()}
        onSelect={(id) => void restoreSession(id)}
        onDelete={(id) => void deleteConversation(id)}
      />

      {/* 视频窗口 */}
      <div className="relative flex min-h-[300px] flex-col overflow-hidden rounded-[20px] border border-line shadow-[0_18px_40px_rgba(0,0,0,0.35)]">
        <div className="absolute inset-0 bg-[radial-gradient(120%_90%_at_50%_0%,rgba(255,180,84,0.16)_0%,transparent_55%),radial-gradient(80%_60%_at_85%_100%,rgba(124,184,255,0.12)_0%,transparent_60%),linear-gradient(180deg,#312840_0%,#3a2c44_100%)]" />
        <div className="absolute inset-x-0 top-0 z-10 flex items-center justify-between bg-linear-to-b from-black/30 to-transparent px-3.5 py-3">
          <div className="flex items-center gap-1.5 text-[13px] font-semibold">
            <span className="h-2 w-2 animate-pulse rounded-full bg-green shadow-[0_0_8px_#7ed6a0]" />
            小悟 · 视频陪伴中
          </div>
          <div className="rounded-full bg-white/8 px-2.5 py-1 text-[11px] text-muted">
            各学各的
          </div>
        </div>

        <div className="relative z-10 flex flex-1 flex-col items-center justify-center pt-8">
          <div
            className="grid h-[150px] w-[150px] cursor-pointer place-items-center"
            onClick={() => userSay("陪我聊聊天吧")}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={BUDDIES[buddy].src}
              alt="搭子形象"
              draggable={false}
              className="h-36 w-36 rounded-full border-[3px] border-white/16 object-cover object-[center_35%] shadow-[0_18px_40px_rgba(0,0,0,0.45)]"
            />
          </div>
          <div className="mt-2 text-center">
            <div className="text-base font-bold tracking-wide">小悟</div>
            <div className="mt-0.5 text-[11px] text-muted">
              {talking ? "正在说话…" : "安静陪着你 · 需要就叫我"}
            </div>
            <div className="mt-2.5 flex gap-2">
              {(["male", "female"] as Buddy[]).map((b) => (
                <button
                  key={b}
                  type="button"
                  onClick={() => switchBuddy(b)}
                  className={`rounded-full px-3.5 py-1.5 text-[13px] transition-all ${
                    buddy === b
                      ? "bg-linear-to-br from-accent to-accent-2 font-bold text-[#241a0e]"
                      : "bg-surface text-muted"
                  }`}
                >
                  {b === "male" ? "👨🏻 男生" : "👩🏻 女生"}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 字幕 */}
      <div className="min-h-[30px] px-0.5 text-[17px] font-medium leading-relaxed">
        {subtitle}
        {typing && <span className="text-accent">▍</span>}
      </div>

      {/* 快捷回复 */}
      <div className="flex flex-wrap gap-2">
        {QUICK_REPLIES.map((r) => (
          <button
            key={r.q}
            type="button"
            onClick={() => userSay(r.q)}
            className="rounded-full bg-surface px-3.5 py-2 text-[13px] text-foreground transition active:scale-95"
          >
            {r.label}
          </button>
        ))}
      </div>

      {/* 聊天历史 */}
      <div
        ref={chatRef}
        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-0.5 py-1"
      >
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`max-w-[85%] rounded-[14px] px-3 py-2 text-sm leading-relaxed ${
              m.role === "buddy"
                ? "self-start rounded-bl-[4px] border border-line bg-white/8"
                : "self-end rounded-br-[4px] bg-linear-to-br from-accent to-accent-2 font-medium text-[#241a0e]"
            }`}
          >
            {m.safety ? <SafetyMessage text={m.text} /> : m.text}
            {m.role === "buddy" && !m.safety &&
              m.actions?.map((action) => (
                <AgentActionCard key={action.confirmationToken} action={action} />
              ))}
          </div>
        ))}
      </div>

      {/* 输入栏 */}
      <div className="flex gap-2 pb-0 pt-2">
        {micSupported && (
          <button
            type="button"
            onPointerDown={(e) => {
              e.preventDefault();
              startListening();
            }}
            onPointerUp={(e) => {
              e.preventDefault();
              stopListening();
            }}
            onPointerCancel={stopListening}
            disabled={!voiceEnabled}
            className={`grid h-[50px] w-[50px] shrink-0 touch-none select-none place-items-center rounded-full border border-line text-xl ${
              listening
                ? "bg-linear-to-br from-danger to-accent-2 text-white"
                : "bg-surface text-foreground"
            } disabled:cursor-not-allowed disabled:opacity-35`}
            aria-label="按住说话"
            title="按住说话"
          >
            🎤
          </button>
        )}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send();
          }}
          maxLength={200}
          placeholder={listening ? "正在听…松开结束" : "和搭子说句话…"}
          className="min-w-0 flex-1 rounded-full border border-line bg-surface px-4 py-3 text-[15px] text-foreground outline-none placeholder:text-muted focus:border-accent/50"
        />
        <button
          type="button"
          onClick={send}
          disabled={busy}
          className="grid h-[50px] w-[50px] shrink-0 place-items-center rounded-full bg-linear-to-br from-accent to-accent-2 text-xl text-[#241a0e] active:scale-90 disabled:opacity-40"
          aria-label="发送"
        >
          ➤
        </button>
      </div>
      {micMessage && <p className="px-1 text-xs text-muted">{micMessage}</p>}
    </div>
  );
}
