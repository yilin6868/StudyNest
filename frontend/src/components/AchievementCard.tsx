"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { Achievement } from "@/lib/api/types";
export default function AchievementCard() {
  const [items, setItems] = useState<Achievement[]>([]);
  useEffect(() => { api.getAchievements().then(setItems).catch(() => undefined); }, []);
  if (!items.length) return null;
  return <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4"><div className="mb-2 text-[15px] font-bold">学习里程碑</div><div className="space-y-2">{items.map((item) => <div key={item.code} className="rounded-xl bg-white/5 p-2"><div className="text-sm font-semibold">{item.title}</div><div className="text-xs text-muted">{item.description}</div></div>)}</div></div>;
}
