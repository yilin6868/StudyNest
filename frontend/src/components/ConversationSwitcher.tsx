"use client";

import type { ConversationSummary } from "@/lib/api/types";

export default function ConversationSwitcher({
  sessions,
  currentId,
  busy,
  onNew,
  onSelect,
  onDelete,
}: {
  sessions: ConversationSummary[];
  currentId: string | null;
  busy: boolean;
  onNew: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
}) {
  return (
    <details className="rounded-xl border border-line bg-surface px-3 py-2">
      <summary className="cursor-pointer text-sm font-semibold">最近对话</summary>
      <button
        type="button"
        onClick={onNew}
        disabled={busy}
        className="mt-2 w-full rounded-lg bg-white/8 px-3 py-2 text-left text-sm"
      >
        ＋ 新对话
      </button>
      <div className="mt-2 max-h-40 space-y-1 overflow-y-auto">
        {sessions.map((item) => (
          <div key={item.sessionId} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onSelect(item.sessionId)}
              disabled={busy}
              className={`min-w-0 flex-1 truncate rounded-lg px-2 py-1.5 text-left text-xs ${
                currentId === item.sessionId ? "bg-accent/20 text-accent" : "text-muted"
              }`}
            >
              {item.title || "新对话"}
            </button>
            <button
              type="button"
              aria-label={`删除对话 ${item.title || "新对话"}`}
              onClick={() => onDelete(item.sessionId)}
              disabled={busy}
              className="rounded px-2 py-1 text-xs text-muted"
            >
              删除
            </button>
          </div>
        ))}
      </div>
    </details>
  );
}

