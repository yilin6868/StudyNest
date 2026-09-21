"use client";

export default function SafetyMessage({ text }: { text: string }) {
  return (
    <div
      className="rounded-xl border border-danger/45 bg-danger/10 p-3"
      data-testid="safety-message"
      role="status"
    >
      <p className="mb-1 text-xs font-bold text-danger">安全提醒</p>
      <p className="whitespace-pre-wrap text-sm leading-relaxed">{text}</p>
    </div>
  );
}

