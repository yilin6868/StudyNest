"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";

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
}

export default function ChatPage() {
  const [buddy, setBuddy] = useState<Buddy>(() => {
    if (typeof window === "undefined") return "male";
    return localStorage.getItem("sb_buddy") === "female" ? "female" : "male";
  });
  const [voiceOn, setVoiceOn] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("sb_voice") === "1"; // 默认关闭，仅显式开启才为 true
  });
  const [messages, setMessages] = useState<Msg[]>([]);
  const [subtitle, setSubtitle] = useState("……");
  const [typing, setTyping] = useState(false);
  const [talking, setTalking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const typeTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechGenRef = useRef(0);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const listeningRef = useRef(false);
  const finalTranscriptRef = useRef("");
  const chatRef = useRef<HTMLDivElement>(null);

  // ==================== 说话 ====================
  function stopSpeech() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (typeTimerRef.current) {
      clearInterval(typeTimerRef.current);
      typeTimerRef.current = null;
    }
    setTyping(false);
    setTalking(false);
  }

  function speak(text: string) {
    stopSpeech();
    const gen = ++speechGenRef.current;

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
        setMessages((m) => [...m, { role: "buddy", text }]);
      }
    }, 30);

    // 语音播放
    if (voiceOn) {
      api.tts(text, BUDDIES[buddy].gender).then((url) => {
        if (url && gen === speechGenRef.current) {
          const audio = new Audio(url);
          audioRef.current = audio;
          setTalking(true);
          audio.onended = () => {
            URL.revokeObjectURL(url);
            if (audioRef.current === audio) audioRef.current = null;
            setTalking(false);
          };
          audio.play().catch(() => {
            URL.revokeObjectURL(url);
            if (audioRef.current === audio) audioRef.current = null;
            setTalking(false);
          });
        }
      });
    }
  }

  async function userSay(text: string) {
    if (!text.trim() || busy) return;
    stopSpeech();
    setMessages((m) => [...m, { role: "user", text }]);
    setBusy(true);
    try {
      const d = await api.chat(text);
      speak(d.reply);
    } catch {
      speak("哎呀，我这边信号不太好，稍等再试");
    } finally {
      setBusy(false);
    }
  }

  // ==================== 初始化 ====================
  const speakRef = useRef<((text: string) => void) | null>(null);

  // 每次渲染后把最新 speak 写入 ref（供异步回调和空依赖 effect 使用）
  useEffect(() => {
    speakRef.current = speak;
  });

  useEffect(() => {
    api
      .encourage("greet")
      .then((d) => speakRef.current?.(d.reply))
      .catch(() => speakRef.current?.("来啦？今天状态怎么样？"));
  }, []);

  // 卸载清理
  useEffect(() => {
    return () => {
      if (audioRef.current) audioRef.current.pause();
      if (typeTimerRef.current) clearInterval(typeTimerRef.current);
    };
  }, []);

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
    setBuddy(b);
    localStorage.setItem("sb_buddy", b);
  }

  function toggleVoice() {
    setVoiceOn((v) => {
      const next = !v;
      localStorage.setItem("sb_voice", next ? "1" : "0");
      if (!next) stopSpeech();
      return next;
    });
  }

  // ==================== 语音输入 ====================
  useEffect(() => {
    const SR =
      window.SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: SpeechRecognitionConstructor })
        .webkitSpeechRecognition;
    if (!SR) return;

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
        speakRef.current?.("麦克风权限没开，用打字也行～");
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startListening() {
    const rec = recognitionRef.current;
    if (!rec || listeningRef.current || !voiceOn) return;
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

  const micSupported =
    typeof window !== "undefined" &&
    (window.SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: unknown })
        .webkitSpeechRecognition);

  return (
    <div className="flex h-full flex-col gap-3 p-3 pb-2">
      {/* 语音开关 */}
      <div className="flex items-center justify-between px-1">
        <span className="text-sm text-muted">语音</span>
        <button
          type="button"
          role="switch"
          aria-checked={voiceOn}
          onClick={toggleVoice}
          className={`relative h-[26px] w-[46px] rounded-full transition-colors ${
            voiceOn
              ? "bg-linear-to-br from-accent to-accent-2"
              : "bg-white/12"
          }`}
        >
          <span
            className={`absolute top-[3px] h-5 w-5 rounded-full bg-white shadow transition-all ${
              voiceOn ? "left-[23px]" : "left-[3px]"
            }`}
          />
        </button>
      </div>

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
            {m.text}
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
            disabled={!voiceOn}
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
    </div>
  );
}
