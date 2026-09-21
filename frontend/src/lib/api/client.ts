import { clearToken, getToken } from "@/lib/auth";
import type {
  ApiErrorBody,
  AgentResponse,
  EncourageResponse,
  EncourageScene,
  History,
  SessionResponse,
  Stats,
  AuthResponse,
  FocusSnapshot,
  FocusSummaryResponse,
  Goal,
  ResolveAgentActionResponse,
  ConversationMessages,
  ConversationSummary,
  LearningMemory,
  MemoryCategory,
  CompanionPreferences,
  Achievement, FocusOptions,
} from "./types";

const BASE = "/api/v1";

/** 统一 API 错误：把后端错误结构归一化，供 UI 显示 userMessage。 */
export class ApiRequestError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
  }
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function redirectToLogin() {
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    clearToken();
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { ...authHeaders(), ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiRequestError(0, "NETWORK_ERROR", "网络连接失败，请稍后再试");
  }

  if (res.status === 401 && path !== "/auth/login") {
    redirectToLogin();
    throw new ApiRequestError(401, "UNAUTHORIZED", "登录已过期，请重新登录");
  }

  if (!res.ok) {
    let code = `HTTP_${res.status}`;
    let message = "请求失败";
    try {
      const body = (await res.json()) as ApiErrorBody;
      if (body?.error) {
        code = body.error.code;
        message = body.error.message;
      }
    } catch {
      /* 非 JSON 响应 */
    }
    throw new ApiRequestError(res.status, code, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const jsonHeaders = { "Content-Type": "application/json" };

function parseAgentResponse(value: AgentResponse): AgentResponse {
  const validAction = value.actions?.every((action) => {
    if (
      typeof action.confirmationToken !== "string" ||
      action.confirmationToken.length < 32 ||
      typeof action.expiresAt !== "string"
    ) return false;
    if (action.type === "confirm_pause_focus") return true;
    return (
      action.type === "confirm_start_focus" &&
      Number.isInteger(action.durationMinutes) &&
      action.durationMinutes >= 5 &&
      action.durationMinutes <= 120
    );
  });
  if (
    value.protocolVersion !== "1.2" ||
    typeof value.requestId !== "string" ||
    typeof value.sessionId !== "string" ||
    typeof value.reply !== "string" ||
    !["llm", "local"].includes(value.source) ||
    !["normal", "safety"].includes(value.responseMode) ||
    !Array.isArray(value.actions) ||
    !validAction ||
    (value.responseMode === "safety" && value.actions.length > 0)
  ) {
    throw new ApiRequestError(502, "INVALID_AGENT_RESPONSE", "搭子返回了无法识别的操作");
  }
  return value;
}

function parseResolvedAction(value: ResolveAgentActionResponse): ResolveAgentActionResponse {
  const action = value.action;
  const validAction =
    action === null ||
    action.type === "pause_focus" ||
    (action.type === "start_focus" &&
      Number.isInteger(action.durationMinutes) &&
      action.durationMinutes >= 5 &&
      action.durationMinutes <= 120);
  if (
    typeof value.accepted !== "boolean" ||
    typeof value.message !== "string" ||
    value.accepted !== (action !== null) ||
    !validAction
  ) {
    throw new ApiRequestError(502, "INVALID_AGENT_ACTION", "后端返回了无法识别的操作");
  }
  return value;
}

export const api = {
  login(username: string, password: string) {
    return request<AuthResponse>("/auth/login", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ username, password }),
    });
  },

  demoLogin(inviteCode: string) {
    return request<AuthResponse>("/auth/demo-login", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ inviteCode }) });
  },

  register(inviteCode: string, username: string, password: string) {
    return request<AuthResponse>("/auth/register", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ inviteCode, username, password }),
    });
  },

  logout() {
    return request<void>("/auth/logout", { method: "POST" });
  },

  getSession() {
    return request<SessionResponse>("/auth/session");
  },

  async chat(message: string, focus: FocusSnapshot, sessionId: string | null) {
    const result = await request<AgentResponse>("/chat", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ protocolVersion: "1.2", sessionId, message, focus }),
    });
    return parseAgentResponse(result);
  },

  createChatSession() {
    return request<{ sessionId: string }>("/chat/sessions", { method: "POST" });
  },

  listChatSessions() {
    return request<{ sessions: ConversationSummary[] }>("/chat/sessions");
  },

  getChatMessages(sessionId: string) {
    return request<ConversationMessages>(`/chat/sessions/${sessionId}/messages`);
  },

  deleteChatSession(sessionId: string) {
    return request<void>(`/chat/sessions/${sessionId}`, { method: "DELETE" });
  },

  listMemories() {
    return request<{ memories: LearningMemory[] }>("/memories");
  },

  putMemory(category: MemoryCategory, content: string) {
    return request<LearningMemory>(`/memories/${category}`, {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify({ content }),
    });
  },

  deleteMemory(category: MemoryCategory) {
    return request<void>(`/memories/${category}`, { method: "DELETE" });
  },

  async resolveAgentAction(confirmationToken: string, decision: "confirm" | "reject") {
    const result = await request<ResolveAgentActionResponse>("/agent/actions/resolve", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ protocolVersion: "1.1", confirmationToken, decision }),
    });
    return parseResolvedAction(result);
  },

  focusSummary(sessionId: string) {
    return request<FocusSummaryResponse>("/agent/focus-summary", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ sessionId }),
    });
  },

  getGoal() {
    return request<Goal>("/goal");
  },

  putGoal(text: string) {
    return request<Goal>("/goal", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify({ text }),
    });
  },

  encourage(scene: EncourageScene) {
    return request<EncourageResponse>("/encourage", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ scene }),
    });
  },

  getCompanionPreferences() {
    return request<CompanionPreferences>("/companion/preferences");
  },

  putCompanionPreferences(value: CompanionPreferences) {
    return request<CompanionPreferences>("/companion/preferences", {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(value),
    });
  },

  getFocusOptions() { return request<FocusOptions>("/focus/options"); },
  getAchievements() { return request<Achievement[]>("/achievements"); },
  createRoom(hours = 4) { return request<{ roomId: string; inviteToken: string; expiresAt: string }>("/rooms", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ expires_hours: hours }) }); },
  joinRoom(inviteToken: string) { return request<import("./types").StudyRoom>("/rooms/join", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ invite_token: inviteToken }) }); },
  getRoom(roomId: string) { return request<import("./types").StudyRoom>(`/rooms/${roomId}`); },
  updateRoomStatus(roomId: string, focusStatus: "idle" | "focusing") { return request<{ status: string }>(`/rooms/${roomId}/status`, { method: "PUT", headers: jsonHeaders, body: JSON.stringify({ focus_status: focusStatus }) }); },
  leaveRoom(roomId: string) { return request<void>(`/rooms/${roomId}/leave`, { method: "POST" }); },
  reportRoom(roomId: string, reason: string) { return request<{ accepted: boolean }>(`/rooms/${roomId}/reports`, { method: "POST", headers: jsonHeaders, body: JSON.stringify({ reason }) }); },

  recordProductEvent(eventType: string, sessionId?: string, durationMinutes?: number) {
    return request<{ accepted: boolean }>("/analytics/events", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ eventType, sessionId, durationMinutes }),
    });
  },

  getWeeklySummary() {
    return request<import("./types").LearningSummary>("/summaries/weekly");
  },

  getWeeklyBroadcast() {
    return request<import("./types").LearningSummary>("/summaries/weekly/broadcast");
  },

  getCompanionInbox() {
    return request<{ items: { id: string; type: string; message: string }[] }>("/companion/inbox");
  },

  exportUserData() {
    return request<Record<string, unknown>>("/data/export");
  },

  deleteStudyData(confirmation: string) {
    return request<{ status: string }>("/data/delete-study", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ confirmation }) });
  },

  deleteAccount(confirmation: string) {
    return request<{ status: string }>("/data/delete-account", { method: "POST", headers: jsonHeaders, body: JSON.stringify({ confirmation }) });
  },

  getStats() {
    return request<Stats>("/stats");
  },

  completeTomato(sessionId: string, minutes: number) {
    return request<Stats>("/stats/complete", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ sessionId, minutes }),
    });
  },

  getHistory() {
    return request<History>("/history");
  },

  /** 文字转语音：返回可播放的 ObjectURL；失败/静音返回 null。 */
  async tts(
    text: string,
    gender: "male" | "female",
    signal?: AbortSignal,
  ): Promise<string | null> {
    try {
      const res = await fetch(`${BASE}/tts`, {
        method: "POST",
        headers: { ...jsonHeaders, ...authHeaders() },
        body: JSON.stringify({ text, gender }),
        signal,
      });
      if (!res.ok || res.status === 204) return null;
      const blob = await res.blob();
      if (!blob.size) return null;
      return URL.createObjectURL(blob);
    } catch {
      return null;
    }
  },
};
