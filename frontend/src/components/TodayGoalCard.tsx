"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api/client";

export default function TodayGoalCard({
  readOnly = false,
  refreshKey = 0,
}: {
  readOnly?: boolean;
  refreshKey?: number;
}) {
  const [text, setText] = useState("");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const goal = await api.getGoal();
      setText(goal.text);
      setDraft(goal.text);
      setNotice("");
    } catch {
      setNotice("目标暂时加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, [load, refreshKey]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      void load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load]);

  async function save() {
    if (busy) return;
    setBusy(true);
    try {
      const goal = await api.putGoal(draft.trim());
      setText(goal.text);
      setDraft(goal.text);
      setNotice("已保存");
    } catch {
      setNotice("保存失败，请稍后重试");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-[16px] border border-line bg-surface px-3.5 py-3" aria-label="今日目标">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-bold">🎯 今日目标</h2>
        {notice && <span className="text-[11px] text-muted" aria-live="polite">{notice}</span>}
      </div>
      {readOnly ? (
        <p className="text-sm text-foreground">{text || "今天还没有设置目标"}</p>
      ) : (
        <div className="flex gap-2">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            disabled={loading}
            maxLength={60}
            placeholder="今天准备完成什么？"
            className="min-w-0 flex-1 rounded-xl border border-line bg-black/15 px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent/50"
          />
          <button
            type="button"
            onClick={save}
            disabled={loading || busy || draft.trim() === text}
            className="rounded-xl bg-linear-to-br from-accent to-accent-2 px-3 py-2 text-sm font-bold text-[#241a0e] disabled:opacity-40"
          >
            {loading ? "加载中" : busy ? "保存中" : "保存"}
          </button>
        </div>
      )}
    </section>
  );
}
