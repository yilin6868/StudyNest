"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiRequestError } from "@/lib/api/client";
import type { AgentAction } from "@/lib/api/types";
import { applyResolvedAgentAction } from "@/lib/agent-actions";

export default function AgentActionCard({ action }: { action: AgentAction }) {
  const router = useRouter();
  const [status, setStatus] = useState<"pending" | "busy" | "done">("pending");
  const [notice, setNotice] = useState("");

  async function resolve(decision: "confirm" | "reject") {
    if (status !== "pending") return;
    setStatus("busy");
    let backendAccepted = false;
    try {
      const result = await api.resolveAgentAction(action.confirmationToken, decision);
      if (result.accepted && result.action) {
        backendAccepted = true;
        applyResolvedAgentAction(result.action);
        setNotice(result.message);
        setStatus("done");
        if (result.action.type === "start_focus") router.push("/focus");
        return;
      }
      setNotice(result.message);
      setStatus("done");
    } catch (error) {
      const message =
        backendAccepted
          ? "后端已经确认，但本地计时操作失败，请到专注页手动处理。"
          : error instanceof ApiRequestError && error.status === 409
          ? "这个确认已过期或处理过，请重新告诉小悟。"
          : error instanceof Error
            ? error.message
            : "操作失败，请稍后重试";
      setNotice(message);
      setStatus("done");
    }
  }

  return (
    <div className="mt-2 rounded-xl border border-accent/30 bg-black/15 p-3" data-testid="agent-action-card">
      <p className="text-sm font-semibold">
        {action.type === "confirm_start_focus"
          ? `开始 ${action.durationMinutes} 分钟专注？`
          : "暂停当前专注？"}
      </p>
      {status === "pending" ? (
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={() => void resolve("confirm")}
            className="rounded-lg bg-linear-to-br from-accent to-accent-2 px-3 py-1.5 text-xs font-bold text-[#241a0e]"
          >
            确认
          </button>
          <button
            type="button"
            onClick={() => void resolve("reject")}
            className="rounded-lg border border-line px-3 py-1.5 text-xs text-muted"
          >
            取消
          </button>
        </div>
      ) : status === "busy" ? (
        <p className="mt-2 text-xs text-muted">正在处理…</p>
      ) : (
        <p className="mt-2 text-xs text-muted" aria-live="polite">{notice}</p>
      )}
    </div>
  );
}
