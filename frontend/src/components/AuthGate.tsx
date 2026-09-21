"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, ApiRequestError } from "@/lib/api/client";
import { clearToken, getToken } from "@/lib/auth";
import BottomNav from "@/components/layout/BottomNav";

type AuthState = "checking" | "authenticated" | "unauthenticated" | "network_error";

interface AuthCheck {
  pathname: string;
  state: AuthState;
}

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authCheck, setAuthCheck] = useState<AuthCheck>({ pathname: "", state: "checking" });
  const [retryKey, setRetryKey] = useState(0);
  const isLogin = pathname === "/login";

  useEffect(() => {
    if (isLogin) return;

    let cancelled = false;
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }

    api
      .getSession()
      .then(() => {
        if (!cancelled) setAuthCheck({ pathname, state: "authenticated" });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiRequestError && error.status === 401) {
          clearToken();
          setAuthCheck({ pathname, state: "unauthenticated" });
          router.replace("/login");
          return;
        }
        setAuthCheck({ pathname, state: "network_error" });
      });

    return () => {
      cancelled = true;
    };
  }, [isLogin, pathname, retryKey, router]);

  if (isLogin) return <main className="flex-1">{children}</main>;

  const authState = authCheck.pathname === pathname ? authCheck.state : "checking";

  if (authState === "network_error") {
    return (
      <main className="grid flex-1 place-items-center p-8 text-center">
        <div>
          <p className="text-sm text-muted">暂时无法确认登录状态，请检查网络后重试。</p>
          <button
            type="button"
            onClick={() => {
              setAuthCheck({ pathname, state: "checking" });
              setRetryKey((value) => value + 1);
            }}
            className="mt-4 rounded-full bg-linear-to-br from-accent to-accent-2 px-5 py-2.5 text-sm font-bold text-[#241a0e]"
          >
            重新检查
          </button>
        </div>
      </main>
    );
  }

  if (authState !== "authenticated") {
    return (
      <main className="grid flex-1 place-items-center p-8 text-sm text-muted" aria-live="polite">
        正在确认登录状态…
      </main>
    );
  }

  return (
    <>
      <main className="flex-1">{children}</main>
      <BottomNav />
    </>
  );
}
