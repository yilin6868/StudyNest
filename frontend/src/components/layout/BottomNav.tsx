"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/", label: "陪伴", icon: "💬" },
  { href: "/focus", label: "专注", icon: "🍅" },
  { href: "/profile", label: "我的", icon: "👤" },
];

export default function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="flex shrink-0 gap-2 border-t border-line bg-[#221d2e]/95 px-4 pb-[calc(10px+env(safe-area-inset-bottom))] pt-2.5">
      {tabs.map((t) => {
        const active = pathname === t.href;
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-full px-0 py-2.5 text-sm font-semibold transition-colors ${
              active
                ? "bg-linear-to-br from-accent to-accent-2 text-[#241a0e]"
                : "bg-surface text-muted"
            }`}
          >
            <span aria-hidden>{t.icon}</span>
            <span>{t.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
