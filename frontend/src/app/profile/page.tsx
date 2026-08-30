"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { History, Stats } from "@/lib/api/types";

const EMPTY_STATS: Stats = { date: "", tomato: 0, minutes: 0, streak: 0, weekDays: [] };
const EMPTY_HISTORY: History = { days: {}, totalTomato: 0, totalMinutes: 0 };

const pad2 = (n: number) => String(n).padStart(2, "0");

function fmtMinutes(m: number) {
  m = m || 0;
  if (m < 60) return `${m}分`;
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return mm ? `${h}小时${mm}分` : `${h}小时`;
}

export default function ProfilePage() {
  const [stats, setStats] = useState<Stats>(EMPTY_STATS);
  const [history, setHistory] = useState<History>(EMPTY_HISTORY);
  const now = new Date();
  const [calYear, setCalYear] = useState(now.getFullYear());
  const [calMonth, setCalMonth] = useState(now.getMonth());

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch(() => setStats(EMPTY_STATS));
    api
      .getHistory()
      .then(setHistory)
      .catch(() => setHistory(EMPTY_HISTORY));
  }, []);

  function renderDays() {
    const first = new Date(calYear, calMonth, 1);
    const last = new Date(calYear, calMonth + 1, 0);
    const startDay = first.getDay();
    const totalDays = last.getDate();
    const todayStr = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;

    const cells: React.ReactNode[] = [];
    for (let i = 0; i < startDay; i++) {
      cells.push(<div key={`e${i}`} className="invisible aspect-square" />);
    }
    for (let d = 1; d <= totalDays; d++) {
      const ds = `${calYear}-${pad2(calMonth + 1)}-${pad2(d)}`;
      const done = (history.days[ds]?.tomato ?? 0) > 0;
      const isToday = ds === todayStr;
      cells.push(
        <div
          key={d}
          className={`grid aspect-square place-items-center rounded-lg text-[13px] ${
            done
              ? "bg-linear-to-br from-accent to-accent-2 font-bold text-[#241a0e]"
              : "text-muted"
          } ${isToday ? "border border-accent" : ""}`}
        >
          {d}
        </div>,
      );
    }
    return cells;
  }

  function prevMonth() {
    setCalMonth((m) => {
      if (m === 0) {
        setCalYear((y) => y - 1);
        return 11;
      }
      return m - 1;
    });
  }

  function nextMonth() {
    setCalMonth((m) => {
      if (m === 11) {
        setCalYear((y) => y + 1);
        return 0;
      }
      return m + 1;
    });
  }

  return (
    <div className="flex h-full flex-col gap-3.5 p-3.5 pb-2">
      {/* 统计总览 */}
      <div className="grid grid-cols-2 gap-2.5">
        <div className="flex flex-col gap-1 rounded-2xl border border-line bg-surface px-3.5 py-4">
          <b className="text-2xl font-extrabold">{history.totalTomato}</b>
          <span className="text-xs text-muted">累计番茄</span>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl border border-line bg-surface px-3.5 py-4">
          <b className="text-2xl font-extrabold">{fmtMinutes(history.totalMinutes)}</b>
          <span className="text-xs text-muted">累计时长</span>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl border border-line bg-surface px-3.5 py-4">
          <b className="text-2xl font-extrabold">{stats.streak || 0}</b>
          <span className="text-xs text-muted">连续天数</span>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl border border-line bg-surface px-3.5 py-4">
          <b className="text-2xl font-extrabold">{(stats.weekDays || []).length || 0}</b>
          <span className="text-xs text-muted">本周专注</span>
        </div>
      </div>

      {/* 打卡日历 */}
      <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4">
        <div className="mb-3 flex items-center justify-between">
          <button
            type="button"
            onClick={prevMonth}
            className="grid h-8 w-8 place-items-center rounded-full border border-line bg-white/8 text-lg"
            aria-label="上个月"
          >
            ‹
          </button>
          <span className="text-[15px] font-bold">
            {calYear}年{calMonth + 1}月
          </span>
          <button
            type="button"
            onClick={nextMonth}
            className="grid h-8 w-8 place-items-center rounded-full border border-line bg-white/8 text-lg"
            aria-label="下个月"
          >
            ›
          </button>
        </div>

        <div className="mb-1.5 grid grid-cols-7 text-center text-xs text-muted">
          {["日", "一", "二", "三", "四", "五", "六"].map((w) => (
            <span key={w}>{w}</span>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-1">{renderDays()}</div>
      </div>
    </div>
  );
}
