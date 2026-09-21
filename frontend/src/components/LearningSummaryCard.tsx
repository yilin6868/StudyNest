"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { LearningSummary } from "@/lib/api/types";
import { useVoice } from "@/components/providers/VoiceProvider";

export default function LearningSummaryCard() {
  const [summary, setSummary] = useState<LearningSummary | null>(null);
  const [error, setError] = useState("");
  const { speak } = useVoice();
  useEffect(() => {
    api.getWeeklySummary().then(setSummary).catch(() => setError("本周总结暂时无法读取"));
  }, []);
  if (error) return <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4 text-sm text-muted">{error}</div>;
  if (!summary) return <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4 text-sm text-muted">正在整理本周学习…</div>;
  return (
    <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4">
      <div className="mb-2 text-[15px] font-bold">本周学习总结</div>
      <div className="mb-2 text-xs text-muted">{summary.period.replace("/", " 至 ")}</div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs text-muted">
        <div><b className="block text-lg text-foreground">{summary.facts.study_days}</b>学习天数</div>
        <div><b className="block text-lg text-foreground">{summary.facts.completed_sessions}</b>完成次数</div>
        <div><b className="block text-lg text-foreground">{summary.facts.total_minutes}</b>分钟</div>
      </div>
      <p className="mt-3 text-sm leading-relaxed">{summary.text}</p>
      <button type="button" onClick={() => void speak(summary.text, "female")} className="mt-3 rounded-full border border-line px-3 py-1 text-xs text-muted">朗读本周总结</button>
    </div>
  );
}
