"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import Logo from "@/components/Logo";
import { ApiError, authApi, type User } from "@/lib/api";

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let active = true;
    authApi
      .me()
      .then((u) => {
        if (active) setUser(u);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.push("/login");
        }
      });
    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!menuRef.current) return;
      if (!menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const onLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore
    }
    router.push("/login");
    router.refresh();
  };

  const initial = user?.email ? user.email[0].toUpperCase() : "?";

  return (
    <header className="border-b border-white/8 px-6 h-14 flex items-center">
      <div className="max-w-5xl w-full mx-auto flex items-center justify-between">
        <Logo />
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="h-8 w-8 rounded-full bg-white/10 hover:bg-white/15 text-xs font-medium flex items-center justify-center"
            aria-label="사용자 메뉴"
          >
            {initial}
          </button>
          {open ? (
            <div className="absolute right-0 mt-2 w-56 rounded-2xl bg-[var(--background-elevated-2)] border border-white/8 py-2 text-sm">
              <div className="px-4 py-2 text-xs text-white/50 truncate">
                {user?.email ?? "..."}
              </div>
              <div className="my-1 h-px bg-white/8" />
              <button
                onClick={onLogout}
                className="w-full px-4 py-2 flex items-center gap-2 text-left hover:bg-white/5 text-white/80 hover:text-white"
              >
                <LogOut className="h-3.5 w-3.5" strokeWidth={1.5} />
                로그아웃
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
