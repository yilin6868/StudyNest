"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { CompanionPreferences as Preferences } from "@/lib/api/types";

const DEFAULTS: Preferences = {
  mid_session_encouragement_enabled: false,
  proactive_reminder_enabled: false,
  quiet_hours_start: null,
  quiet_hours_end: null,
  custom_focus_enabled: false,
  default_focus_minutes: 25,
  reminder_channel: "in_app",
};

export default function CompanionPreferences() {
  const [value, setValue] = useState<Preferences>(DEFAULTS);
  const [status, setStatus] = useState("");

  useEffect(() => {
    api.getCompanionPreferences().then(setValue).catch(() => setStatus("主动陪伴设置暂时无法读取"));
  }, []);

  async function update(next: Preferences) {
    const previous = value;
    setValue(next);
    setStatus("保存中…");
    try {
      setValue(await api.putCompanionPreferences(next));
      setStatus("已保存");
    } catch {
      setValue(previous);
      setStatus("保存失败，请重试");
    }
  }

  return (
    <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4">
      <div className="mb-3 text-[15px] font-bold">主动陪伴</div>
      <label className="flex items-center justify-between py-2 text-sm">
        <span>专注过半时鼓励</span>
        <input
          type="checkbox"
          checked={value.mid_session_encouragement_enabled}
          onChange={(e) => update({ ...value, mid_session_encouragement_enabled: e.target.checked })}
        />
      </label>
      <label className="flex items-center justify-between py-2 text-sm">
        <span>允许自定义专注时长</span>
        <input type="checkbox" checked={value.custom_focus_enabled} onChange={(e) => update({ ...value, custom_focus_enabled: e.target.checked })} />
      </label>
      {value.custom_focus_enabled && <select className="mt-1 w-full rounded bg-black/20 p-2 text-sm" value={value.default_focus_minutes} onChange={(e) => update({ ...value, default_focus_minutes: Number(e.target.value) })}>
        {[15, 25, 45, 60].map((minutes) => <option key={minutes} value={minutes}>{minutes} 分钟</option>)}
      </select>}
      <label className="flex items-center justify-between py-2 text-sm">
        <span>允许主动提醒</span>
        <input
          type="checkbox"
          checked={value.proactive_reminder_enabled}
          onChange={(e) => update({ ...value, proactive_reminder_enabled: e.target.checked })}
        />
      </label>
      <div className="mt-1 text-xs text-muted">首版只在应用内提示，不发送站外通知。</div>
      {status && <div className="mt-2 text-xs text-muted" aria-live="polite">{status}</div>}
    </div>
  );
}
