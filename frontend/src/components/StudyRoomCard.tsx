"use client";
import { useState } from "react";
import { api } from "@/lib/api/client";
export default function StudyRoomCard() {
  const [room, setRoom] = useState<{ roomId: string; inviteToken: string } | null>(null);
  const [join, setJoin] = useState(""); const [message, setMessage] = useState("");
  async function create() { try { const r = await api.createRoom(); setRoom(r); setMessage(`邀请码：${r.inviteToken}`); } catch { setMessage("创建失败，请稍后重试"); } }
  async function joinRoom() { try { const r = await api.joinRoom(join.trim()); setMessage(`已加入，自习室内有 ${r.members.length} 人`); } catch { setMessage("邀请码无效或自习室已过期"); } }
  return <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4"><div className="mb-2 text-[15px] font-bold">多人自习室（实验）</div><div className="text-xs text-muted">只共享在线/专注状态，不共享聊天、目标或记忆。</div><div className="mt-3 flex gap-2"><button type="button" onClick={create} className="rounded-full border border-line px-3 py-1 text-xs">创建</button><input value={join} onChange={(e) => setJoin(e.target.value)} placeholder="输入邀请码" className="min-w-0 flex-1 rounded-full border border-line bg-black/10 px-3 py-1 text-xs" /><button type="button" onClick={joinRoom} className="rounded-full border border-line px-3 py-1 text-xs">加入</button></div>{message && <div className="mt-2 break-all text-xs text-muted" aria-live="polite">{message}</div>}{room && <button type="button" onClick={() => navigator.clipboard?.writeText(room.inviteToken)} className="mt-2 text-xs text-accent">复制邀请码</button>}</div>;
}
