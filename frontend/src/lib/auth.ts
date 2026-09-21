const TOKEN_KEY = "sb_token";
const SESSION_STATE_KEYS = ["sb_timer", "sb_chat_session"];

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function logoutLocal() {
  clearToken();
  for (const key of SESSION_STATE_KEYS) localStorage.removeItem(key);
}

export function isLoggedIn(): boolean {
  return !!getToken();
}
