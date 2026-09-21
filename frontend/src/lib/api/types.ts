export type ChatSource = "llm" | "local";

export type AgentAction =
  | {
      type: "confirm_start_focus";
      durationMinutes: number;
      confirmationToken: string;
      expiresAt: string;
    }
  | {
      type: "confirm_pause_focus";
      confirmationToken: string;
      expiresAt: string;
    };

export interface AgentResponse {
  protocolVersion: "1.2";
  requestId: string;
  sessionId: string;
  reply: string;
  source: ChatSource;
  responseMode: "normal" | "safety";
  actions: AgentAction[];
}

export interface ConversationSummary {
  sessionId: string;
  title: string | null;
  status: "active" | "archived";
  updatedAt: string;
}

export interface ConversationMessage {
  role: "user" | "assistant" | "safety_marker";
  content: string;
  createdAt: string;
}

export interface ConversationMessages {
  sessionId: string;
  messages: ConversationMessage[];
}

export type MemoryCategory =
  | "study_routine"
  | "learning_preference"
  | "companionship_style";

export interface LearningMemory {
  category: MemoryCategory;
  content: string;
  updatedAt: string;
}

export type FocusSnapshot = {
  status: "idle" | "running" | "paused" | "pending_settlement" | "settlement_failed";
  mode: "focus" | "break";
  remainingSeconds: number;
};

export type ResolvedAgentAction =
  | { type: "start_focus"; durationMinutes: number }
  | { type: "pause_focus" };

export interface ResolveAgentActionResponse {
  accepted: boolean;
  action: ResolvedAgentAction | null;
  message: string;
}

export interface FocusSummaryResponse {
  sessionId: string;
  reply: string;
  source: ChatSource;
}

export interface Goal {
  text: string;
}

export interface Stats {
  date: string;
  tomato: number;
  minutes: number;
  streak: number;
  weekDays: string[];
}

export interface DayRecord {
  tomato: number;
  minutes: number;
}

export interface History {
  days: Record<string, DayRecord>;
  totalTomato: number;
  totalMinutes: number;
}

export interface EncourageResponse {
  reply: string;
}

export interface CompanionPreferences {
  mid_session_encouragement_enabled: boolean;
  proactive_reminder_enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  custom_focus_enabled: boolean;
  default_focus_minutes: number;
  reminder_channel: "in_app";
}

export interface Achievement { code: string; title: string; description: string; awarded_at: string; hidden: boolean; }
export interface FocusOptions { enabled: boolean; options: number[]; default_minutes: number; }
export interface StudyRoom { roomId: string; status: string; expiresAt: string; members: { userId: string; focusStatus: string }[]; }

export interface LearningSummary {
  period: string;
  facts: { study_days: number; completed_sessions: number; total_minutes: number; goals_set: number; data_quality: string };
  text: string;
  source: "model" | "local_fallback";
}

export interface SessionResponse {
  authenticated: true;
  userId: string;
  username?: string | null;
}

export interface AuthResponse {
  token: string;
  user_id: string;
}

export type EncourageScene =
  | "greet"
  | "start"
  | "encourage"
  | "celebrate"
  | "break"
  | "breakOver"
  | "tired"
  | "idle";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}
