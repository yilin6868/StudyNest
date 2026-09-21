"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const [mode, setMode] = useState<"demo" | "login" | "register">("demo");
  const [inviteCode, setInviteCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function submit() {
    const name = username.trim();
    if (loading) return;
    if (mode === "demo" && !inviteCode.trim()) return;
    if (mode !== "demo" && (!name || !password)) return;
    if (mode === "register" && !inviteCode.trim()) return;
    if (mode === "register" && (name.length < 3 || name.length > 32)) {
      setError("用户名需要 3 到 32 个字符");
      return;
    }
    if (
      mode === "register" &&
      (password.length < 8 || !/\p{L}/u.test(password) || !/\d/.test(password))
    ) {
      setError("密码至少 8 位，并同时包含字母和数字");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data =
        mode === "demo"
          ? await api.demoLogin(inviteCode.trim())
          : mode === "login"
          ? await api.login(name, password)
          : await api.register(inviteCode.trim(), name, password);
      setToken(data.token);
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败，请重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-8 p-8">
      <div className="text-center">
        <div className="text-4xl">🦉</div>
        <h1 className="mt-3 text-xl font-bold">StudyNest · 自习室</h1>
        <p className="mt-2 text-sm text-muted">登录你的账号，继续专注学习</p>
      </div>

      <div className="w-full max-w-[300px]">
        <div className="mb-4 grid grid-cols-3 rounded-full border border-line bg-surface p-1">
          {(["demo", "login", "register"] as const).map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => {
                setMode(item);
                setError("");
              }}
              className={`rounded-full py-2 text-sm ${mode === item ? "bg-accent font-bold text-[#241a0e]" : "text-muted"}`}
            >
                {item === "demo" ? "体验版" : item === "login" ? "已有账号" : "注册账号"}
            </button>
          ))}
        </div>
        {mode !== "login" && (
          <input
            aria-label="邀请码"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value)}
            placeholder="邀请码"
            maxLength={128}
            autoComplete="off"
            className="mb-3 w-full rounded-full border border-line bg-surface px-5 py-3.5 text-center text-[15px] text-foreground outline-none placeholder:text-muted focus:border-accent/50"
          />
        )}
        {mode !== "demo" && <><input
          aria-label="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="用户名"
          maxLength={64}
          autoComplete="username"
          className="mb-3 w-full rounded-full border border-line bg-surface px-5 py-3.5 text-center text-[15px] text-foreground outline-none placeholder:text-muted focus:border-accent/50"
        />
        <input
          aria-label="密码"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && mode === "login") submit();
          }}
          placeholder="密码（至少 8 位，含字母和数字）"
          maxLength={128}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          className="mb-3 w-full rounded-full border border-line bg-surface px-5 py-3.5 text-center text-[15px] text-foreground outline-none placeholder:text-muted focus:border-accent/50"
        /></>}
        {mode === "register" && (
          <input
            aria-label="确认密码"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
            placeholder="再次输入密码"
            maxLength={128}
            autoComplete="new-password"
            className="w-full rounded-full border border-line bg-surface px-5 py-3.5 text-center text-[15px] text-foreground outline-none placeholder:text-muted focus:border-accent/50"
          />
        )}
        {error && <p className="mt-2 text-center text-sm text-danger">{error}</p>}
        <button
          type="button"
          onClick={submit}
          disabled={
            loading ||
            (mode === "demo" ? !inviteCode.trim() : !username.trim() || !password || (mode === "register" && (!inviteCode.trim() || !confirmPassword)))
          }
          className="mt-4 w-full rounded-full bg-linear-to-br from-accent to-accent-2 py-3.5 text-[15px] font-bold text-[#241a0e] disabled:opacity-40"
        >
          {loading ? "处理中…" : mode === "demo" ? "输入邀请码直接体验" : mode === "login" ? "登录" : "注册并进入"}
        </button>
      </div>
    </div>
  );
}
