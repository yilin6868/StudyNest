"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function submit() {
    const c = code.trim();
    if (!c || loading) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.login(c);
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
        <h1 className="mt-3 text-xl font-bold">AI 学习搭子 · 自习室</h1>
        <p className="mt-2 text-sm text-muted">输入邀请码进入你的专属自习室</p>
      </div>

      <div className="w-full max-w-[300px]">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submit();
          }}
          placeholder="邀请码"
          maxLength={64}
          className="w-full rounded-full border border-line bg-surface px-5 py-3.5 text-center text-[15px] text-foreground outline-none placeholder:text-muted focus:border-accent/50"
        />
        {error && <p className="mt-2 text-center text-sm text-danger">{error}</p>}
        <button
          type="button"
          onClick={submit}
          disabled={loading || !code.trim()}
          className="mt-4 w-full rounded-full bg-linear-to-br from-accent to-accent-2 py-3.5 text-[15px] font-bold text-[#241a0e] disabled:opacity-40"
        >
          {loading ? "登录中…" : "进入自习室"}
        </button>
      </div>
    </div>
  );
}
