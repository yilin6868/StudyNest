"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import BottomNav from "@/components/layout/BottomNav";

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (pathname !== "/login" && !isLoggedIn()) {
      router.replace("/login");
    }
  }, [pathname, router]);

  const isLogin = pathname === "/login";

  return (
    <>
      <main className="flex-1">{children}</main>
      {!isLogin && <BottomNav />}
    </>
  );
}
