"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";

export default function DataRightsManager() {
  const router = useRouter();
  const [status, setStatus] = useState("");
  async function exportData() {
    if (!window.confirm("导出你的学习记录、聊天和记忆吗？")) return;
    setStatus("正在准备导出…");
    try {
      const data = await api.exportUserData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `studynest-data-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setStatus("已导出，请妥善保管文件");
    } catch {
      setStatus("导出失败，请稍后重试");
    }
  }
  async function deleteStudy() {
    if (!window.confirm("这会删除你的学习目标、专注记录和统计，且不能恢复。继续吗？")) return;
    setStatus("正在删除学习数据…");
    try { await api.deleteStudyData("DELETE STUDY DATA"); setStatus("学习数据已删除"); }
    catch { setStatus("删除失败，请稍后重试"); }
  }
  async function deleteAccount() {
    if (!window.confirm("账号注销不可逆，并会删除账号及其数据。确定继续吗？")) return;
    setStatus("正在注销账号…");
    try { await api.deleteAccount("DELETE ACCOUNT"); router.replace("/login"); }
    catch { setStatus("注销失败，请稍后重试"); }
  }
  return (
    <div className="rounded-[20px] border border-line bg-surface px-3.5 py-4">
      <div className="mb-2 text-[15px] font-bold">我的数据</div>
      <p className="mb-3 text-xs leading-relaxed text-muted">导出仅包含你自己的账号、学习记录、聊天和记忆，不包含密码或 Token。</p>
      <button type="button" onClick={exportData} className="rounded-full border border-line bg-white/8 px-4 py-2 text-sm">导出我的数据</button>
      <div className="mt-3 flex gap-2">
        <button type="button" onClick={deleteStudy} className="rounded-full border border-line px-3 py-2 text-xs text-muted">删除学习数据</button>
        <button type="button" onClick={deleteAccount} className="rounded-full border border-danger/40 px-3 py-2 text-xs text-danger">注销账号</button>
      </div>
      {status && <div className="mt-2 text-xs text-muted" aria-live="polite">{status}</div>}
    </div>
  );
}
