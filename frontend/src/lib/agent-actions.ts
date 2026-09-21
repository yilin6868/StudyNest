import type { FocusSnapshot, ResolvedAgentAction } from "@/lib/api/types";
import {
  createSessionId,
  idleTimer,
  restoreTimer,
  TIMER_KEY,
  TIMER_SCHEMA_VERSION,
  type TimerState,
} from "@/lib/timer";

export function getFocusSnapshot(): FocusSnapshot {
  if (typeof window === "undefined") {
    return { status: "idle", mode: "focus", remainingSeconds: 0 };
  }
  const timer = restoreTimer(localStorage.getItem(TIMER_KEY)).timer;
  return timer.status === "idle"
    ? { status: "idle", mode: timer.mode, remainingSeconds: 0 }
    : {
        status: timer.status,
        mode: timer.mode,
        remainingSeconds: timer.remainingSeconds,
      };
}

export function applyResolvedAgentAction(action: ResolvedAgentAction): void {
  const current = restoreTimer(localStorage.getItem(TIMER_KEY)).timer;
  if (action.type === "start_focus") {
    if (current.status !== "idle") throw new Error("当前已有计时，不能重复开始");
    const seconds = action.durationMinutes * 60;
    const now = Date.now();
    const next: TimerState = {
      ...idleTimer("focus"),
      schemaVersion: TIMER_SCHEMA_VERSION,
      sessionId: createSessionId(),
      status: "running",
      startedAt: now,
      endAt: now + seconds * 1000,
      remainingSeconds: seconds,
      durationSeconds: seconds,
    };
    localStorage.setItem(TIMER_KEY, JSON.stringify(next));
    return;
  }
  if (current.status !== "running") throw new Error("当前没有正在运行的计时");
  const remaining = current.endAt
    ? Math.max(0, Math.ceil((current.endAt - Date.now()) / 1000))
    : current.remainingSeconds;
  localStorage.setItem(
    TIMER_KEY,
    JSON.stringify({ ...current, status: "paused", endAt: null, remainingSeconds: remaining }),
  );
}
