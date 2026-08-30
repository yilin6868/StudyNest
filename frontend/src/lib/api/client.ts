import { clearToken, getToken } from "@/lib/auth";
import type {
  ApiErrorBody,
  ChatResponse,
  EncourageResponse,
  EncourageScene,
  History,
  Stats,
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

  return (await res.json()) as T;
}

const jsonHeaders = { "Content-Type": "application/json" };

export const api = {
  login(code: string) {
    return request<{ token: string; user_id: string }>("/auth/login", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ code }),
    });
  },

  chat(message: string, goal?: string) {
    return request<ChatResponse>("/chat", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ message, goal }),
    });
  },

  encourage(scene: EncourageScene) {
    return request<EncourageResponse>("/encourage", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ scene }),
    });
  },

  getStats() {
    return request<Stats>("/stats");
  },

  completeTomato(minutes: number) {
    return request<Stats>("/stats/complete", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ minutes }),
    });
  },

  getHistory() {
    return request<History>("/history");
  },

  /** 文字转语音：返回可播放的 ObjectURL；失败/静音返回 null。 */
  async tts(text: string, gender: "male" | "female"): Promise<string | null> {
    try {
      const res = await fetch(`${BASE}/tts`, {
        method: "POST",
        headers: { ...jsonHeaders, ...authHeaders() },
        body: JSON.stringify({ text, gender }),
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
