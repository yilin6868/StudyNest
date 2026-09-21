"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
} from "react";
import { api } from "@/lib/api/client";
import { setStoredString, useStoredString } from "@/lib/browser-storage";

const VOICE_KEY = "sb_voice";

interface VoiceContextValue {
  voiceEnabled: boolean;
  setVoiceEnabled: (enabled: boolean) => void;
  speak: (text: string, gender: "male" | "female") => Promise<void>;
  stop: () => void;
}

const VoiceContext = createContext<VoiceContextValue | null>(null);

export function VoiceProvider({ children }: { children: React.ReactNode }) {
  const voiceEnabled = useStoredString(VOICE_KEY, "0") === "1";
  const enabledRef = useRef(false);
  const requestRef = useRef<AbortController | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const generationRef = useRef(0);

  const stop = useCallback(() => {
    generationRef.current += 1;
    requestRef.current?.abort();
    requestRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  }, []);

  const setVoiceEnabled = useCallback(
    (enabled: boolean) => {
      enabledRef.current = enabled;
      setStoredString(VOICE_KEY, enabled ? "1" : "0");
      if (!enabled) stop();
    },
    [stop],
  );

  const speak = useCallback(
    async (text: string, gender: "male" | "female") => {
      stop();
      if (!enabledRef.current) return;

      const generation = generationRef.current;
      const controller = new AbortController();
      requestRef.current = controller;
      const url = await api.tts(text, gender, controller.signal);
      if (
        !url ||
        controller.signal.aborted ||
        generation !== generationRef.current ||
        !enabledRef.current
      ) {
        if (url) URL.revokeObjectURL(url);
        return;
      }

      requestRef.current = null;
      objectUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;

      const release = () => {
        if (audioRef.current === audio) audioRef.current = null;
        if (objectUrlRef.current === url) {
          URL.revokeObjectURL(url);
          objectUrlRef.current = null;
        }
      };
      audio.onended = release;
      audio.onerror = release;
      try {
        await audio.play();
      } catch {
        release();
      }
    },
    [stop],
  );

  useEffect(() => {
    enabledRef.current = voiceEnabled;
    if (!voiceEnabled) stop();
  }, [stop, voiceEnabled]);

  useEffect(() => stop, [stop]);

  return (
    <VoiceContext.Provider value={{ voiceEnabled, setVoiceEnabled, speak, stop }}>
      {children}
    </VoiceContext.Provider>
  );
}

export function useVoice(): VoiceContextValue {
  const context = useContext(VoiceContext);
  if (!context) throw new Error("useVoice 必须在 VoiceProvider 内使用");
  return context;
}
