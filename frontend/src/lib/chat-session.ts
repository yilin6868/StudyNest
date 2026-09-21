const CHAT_SESSION_KEY = "sb_chat_session";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function getStoredChatSession(): string | null {
  if (typeof window === "undefined") return null;
  const value = localStorage.getItem(CHAT_SESSION_KEY);
  return value && UUID.test(value) ? value : null;
}

export function storeChatSession(sessionId: string) {
  if (UUID.test(sessionId)) localStorage.setItem(CHAT_SESSION_KEY, sessionId);
}

export function clearStoredChatSession() {
  if (typeof window !== "undefined") localStorage.removeItem(CHAT_SESSION_KEY);
}

