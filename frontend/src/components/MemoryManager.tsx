"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api/client";
import type { MemoryCategory } from "@/lib/api/types";

const CATEGORIES: { key: MemoryCategory; label: string; hint: string }[] = [
  { key: "study_routine", label: "学习习惯", hint: "例如：我一般晚上九点学习" },
  { key: "learning_preference", label: "学习偏好", hint: "例如：我喜欢 30 分钟一轮" },
  { key: "companionship_style", label: "陪伴风格", hint: "例如：专注时少一点鼓励" },
];

export default function MemoryManager() {
  const [values, setValues] = useState<Record<MemoryCategory, string>>({
    study_routine: "",
    learning_preference: "",
    companionship_style: "",
  });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listMemories().then(({ memories }) => {
      setValues((current) => {
        const next = { ...current };
        for (const item of memories) next[item.category] = item.content;
        return next;
      });
    }).catch(() => setNotice("记忆加载失败，可以稍后重试。"));
  }, []);

  async function save(category: MemoryCategory) {
    const content = values[category].trim();
    if (!content || busy) return;
    setBusy(true);
    try {
      await api.putMemory(category, content);
      setNotice("已保存，小悟下次聊天会参考。");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "保存失败，请重试。");
    } finally {
      setBusy(false);
    }
  }

  async function remove(category: MemoryCategory) {
    if (busy || !window.confirm("确定删除这条搭子记忆吗？")) return;
    setBusy(true);
    try {
      await api.deleteMemory(category);
      setValues((current) => ({ ...current, [category]: "" }));
      setNotice("已删除，之后的对话不会再使用它。");
    } catch {
      setNotice("删除失败，请重试。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-[20px] border border-line bg-surface px-3.5 py-4">
      <h2 className="text-[15px] font-bold">搭子记忆</h2>
      <p className="mt-1 text-xs leading-relaxed text-muted">
        只保存与学习陪伴有关的偏好。临时情绪、医疗和敏感隐私不会保存。
      </p>
      <div className="mt-3 space-y-3">
        {CATEGORIES.map((item) => (
          <div key={item.key}>
            <label className="text-xs font-semibold" htmlFor={`memory-${item.key}`}>
              {item.label}
            </label>
            <textarea
              id={`memory-${item.key}`}
              value={values[item.key]}
              maxLength={120}
              rows={2}
              placeholder={item.hint}
              onChange={(event) =>
                setValues((current) => ({ ...current, [item.key]: event.target.value }))
              }
              className="mt-1 w-full resize-none rounded-xl border border-line bg-black/10 px-3 py-2 text-sm outline-none focus:border-accent/50"
            />
            <div className="mt-1 flex gap-2">
              <button
                type="button"
                disabled={busy || !values[item.key].trim()}
                onClick={() => void save(item.key)}
                className="rounded-lg bg-accent/20 px-3 py-1 text-xs text-accent disabled:opacity-40"
              >
                保存
              </button>
              <button
                type="button"
                disabled={busy || !values[item.key]}
                onClick={() => void remove(item.key)}
                className="rounded-lg border border-line px-3 py-1 text-xs text-muted disabled:opacity-40"
              >
                删除
              </button>
            </div>
          </div>
        ))}
      </div>
      {notice && <p className="mt-3 text-xs text-muted" aria-live="polite">{notice}</p>}
    </section>
  );
}
