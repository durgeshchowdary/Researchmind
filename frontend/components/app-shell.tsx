"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Activity, BrainCircuit, Database, Files, GitCompareArrows, Home, KeyRound, Link2, LogOut, Search, Settings, SlidersHorizontal, Upload, UserRound } from "lucide-react";
import clsx from "clsx";

import { getCurrentUser, loadCurrentUser, logout } from "@/lib/auth";
import { AuthUser } from "@/types/api";
import { WorkspaceSwitcher } from "./workspace-switcher";


const appLinks = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/search", label: "Search", icon: Search },
  { href: "/ask", label: "Ask", icon: BrainCircuit },
  { href: "/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/evaluation", label: "Evaluation", icon: Activity },
  { href: "/evaluation/builder", label: "Benchmarks", icon: SlidersHorizontal },
  { href: "/playground", label: "Playground", icon: SlidersHorizontal },
  { href: "/index-management", label: "Indexes", icon: Settings },
  { href: "/connectors", label: "Connectors", icon: Link2 },
  { href: "/observability", label: "Ops", icon: Activity },
  { href: "/api-platform", label: "API", icon: KeyRound },
  { href: "/documents", label: "Documents", icon: Files },
  { href: "/upload", label: "Upload", icon: Upload },
];

const publicPaths = new Set(["/", "/login", "/signup"]);
const protectedPrefixes = ["/dashboard", "/upload", "/documents", "/search", "/ask", "/summarizer", "/compare", "/evaluation", "/playground", "/index-management", "/connectors", "/observability", "/api-platform", "/workspace-settings", "/gap-finder"];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [sessionMessage, setSessionMessage] = useState<string | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const isPublicPage = publicPaths.has(pathname);

  useEffect(() => {
    const syncUser = () => {
      setUser(getCurrentUser());
      setAuthReady(true);
    };
    syncUser();
    loadCurrentUser().catch(() => {
      setUser(null);
      setSessionMessage("Your session expired. Please log in again.");
    });
    window.addEventListener("storage", syncUser);
    window.addEventListener("researchmind-auth-change", syncUser);
    return () => {
      window.removeEventListener("storage", syncUser);
      window.removeEventListener("researchmind-auth-change", syncUser);
    };
  }, []);

  useEffect(() => {
    if (authReady && !user && protectedPrefixes.some((prefix) => pathname.startsWith(prefix))) {
      const reason = sessionMessage ? "&reason=session-expired" : "";
      router.replace(`/login?next=${encodeURIComponent(pathname)}${reason}`);
    }
  }, [authReady, pathname, router, sessionMessage, user]);

  const initials = useMemo(() => {
    if (!user?.name) {
      return "RM";
    }
    return user.name
      .split(" ")
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }, [user?.name]);

  function handleLogout() {
    logout();
    router.push("/");
  }

  const visibleLinks = user ? appLinks : appLinks.filter((link) => link.href !== "/dashboard");

  return (
    <div className={clsx("min-h-screen", isPublicPage ? "bg-transparent" : "bg-transparent")}>
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 md:px-6">
          <Link href={user ? "/dashboard" : "/"} className="flex items-center gap-2 text-slate-950">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-cyan text-white shadow-sm">
              <Database className="h-5 w-5" />
            </span>
            <span className="text-base font-semibold tracking-tight">ResearchMind</span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {visibleLinks.map((link) => {
            const Icon = link.icon;
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  "nav-link",
                  active && "nav-link-active",
                )}
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
            })}
          </nav>

          <div className="flex items-center gap-2">
            {user ? (
              <>
                <WorkspaceSwitcher />
                <div className="hidden items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-sm text-slate-700 shadow-sm sm:flex">
                  <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary-soft text-xs font-semibold text-primary-hover">
                    {initials}
                  </span>
                  <span className="max-w-44 truncate">{user.email}</span>
                </div>
                <button type="button" onClick={handleLogout} className="btn-secondary px-3" aria-label="Logout">
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="btn-secondary">
                  Login
                </Link>
                <Link href="/signup" className="btn-primary">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>

        {!isPublicPage ? (
          <nav className="mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 pb-3 md:hidden">
            {appLinks.map((link) => {
              const Icon = link.icon;
              const active = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={clsx(
                    "flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium",
                    active ? "bg-primary-soft text-primary-hover ring-1 ring-primary/15" : "text-slate-600",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {link.label}
                </Link>
              );
            })}
          </nav>
        ) : null}
      </header>
      {!user && !isPublicPage && authReady ? (
        <div className="mx-auto max-w-7xl px-4 py-3 text-sm text-slate-600 md:px-6">
          <UserRound className="mr-2 inline h-4 w-4" />
          Redirecting to login...
        </div>
      ) : null}
      <main className={clsx(isPublicPage ? "" : "page-shell")}>{children}</main>
    </div>
  );
}
