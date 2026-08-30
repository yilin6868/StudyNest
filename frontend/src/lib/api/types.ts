export type ChatSource = "llm" | "local";

export interface ChatResponse {
  reply: string;
  source: ChatSource;
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
