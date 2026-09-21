export const TIMER_KEY = "sb_timer";
export const TIMER_SCHEMA_VERSION = 3;
export const DEFAULT_SECONDS = { focus: 25 * 60, break: 5 * 60 } as const;

export type TimerMode = "focus" | "break";
export type TimerStatus =
  | "idle"
  | "running"
  | "paused"
  | "pending_settlement"
  | "settlement_failed";

export interface TimerState {
  schemaVersion: 3;
  sessionId: string | null;
  mode: TimerMode;
  status: TimerStatus;
  startedAt: number | null;
  endAt: number | null;
  remainingSeconds: number;
  durationSeconds: number;
  halfDone: boolean;
}

export interface TimerRestoreResult {
  timer: TimerState;
  discardedLegacyState: boolean;
}

export function idleTimer(mode: TimerMode = "focus", focusMinutes?: number): TimerState {
  const focusSeconds = focusMinutes && [15, 25, 45, 60].includes(focusMinutes) ? focusMinutes * 60 : DEFAULT_SECONDS.focus;
  return {
    schemaVersion: TIMER_SCHEMA_VERSION,
    sessionId: null,
    mode,
    status: "idle",
    startedAt: null,
    endAt: null,
    remainingSeconds: mode === "focus" ? focusSeconds : DEFAULT_SECONDS.break,
    durationSeconds: mode === "focus" ? focusSeconds : DEFAULT_SECONDS.break,
    halfDone: false,
  };
}

function isTimerStatus(value: unknown): value is TimerStatus {
  return ["idle", "running", "paused", "pending_settlement", "settlement_failed"].includes(
    String(value),
  );
}

export function restoreTimer(raw: string | null, now = Date.now()): TimerRestoreResult {
  if (!raw) return { timer: idleTimer(), discardedLegacyState: false };

  try {
    const stored = JSON.parse(raw) as Partial<Omit<TimerState, "schemaVersion">> & {
      schemaVersion?: number;
    };
    if (stored.schemaVersion !== 2 && stored.schemaVersion !== TIMER_SCHEMA_VERSION) {
      return { timer: idleTimer(), discardedLegacyState: true };
    }

    const mode: TimerMode = stored.mode === "break" ? "break" : "focus";
    if (!isTimerStatus(stored.status)) {
      return { timer: idleTimer(mode), discardedLegacyState: true };
    }

    const storedDuration = Number(stored.durationSeconds);
    const duration =
      stored.schemaVersion === TIMER_SCHEMA_VERSION &&
      Number.isFinite(storedDuration) &&
      storedDuration >= 5 * 60 &&
      storedDuration <= 120 * 60
        ? storedDuration
        : DEFAULT_SECONDS[mode];
    const maximum = duration;
    const storedRemaining = Number(stored.remainingSeconds);
    const remaining = Number.isFinite(storedRemaining)
      ? Math.min(maximum, Math.max(0, storedRemaining))
      : maximum;
    const sessionId = typeof stored.sessionId === "string" ? stored.sessionId : null;
    const base: TimerState = {
      schemaVersion: TIMER_SCHEMA_VERSION,
      sessionId,
      mode,
      status: stored.status,
      startedAt: typeof stored.startedAt === "number" ? stored.startedAt : null,
      endAt: typeof stored.endAt === "number" ? stored.endAt : null,
      remainingSeconds: remaining,
      durationSeconds: duration,
      halfDone: Boolean(stored.halfDone),
    };

    if (base.status === "running") {
      if (!base.endAt || (mode === "focus" && !base.sessionId)) {
        return { timer: idleTimer(mode), discardedLegacyState: true };
      }
      const secondsLeft = Math.ceil((base.endAt - now) / 1000);
      if (secondsLeft > 0) {
        return {
          timer: {
            ...base,
            remainingSeconds: Math.min(maximum, secondsLeft),
            halfDone: secondsLeft <= maximum / 2,
          },
          discardedLegacyState: false,
        };
      }
      if (mode === "focus" && base.sessionId) {
        return {
          timer: { ...base, status: "pending_settlement", remainingSeconds: 0, endAt: null },
          discardedLegacyState: false,
        };
      }
      return { timer: idleTimer("focus"), discardedLegacyState: false };
    }

    if (
      (base.status === "pending_settlement" || base.status === "settlement_failed") &&
      !base.sessionId
    ) {
      return { timer: idleTimer(mode), discardedLegacyState: true };
    }
    return { timer: base, discardedLegacyState: false };
  } catch {
    return { timer: idleTimer(), discardedLegacyState: true };
  }
}

export function createSessionId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex
    .slice(6, 8)
    .join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}
