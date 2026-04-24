"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, LoaderCircle } from "lucide-react";

import { login, loginWithDemoAccount } from "@/lib/auth";


export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(
    searchParams.get("reason") === "session-expired" ? "Your session expired. Please log in again." : null,
  );

  async function finishLogin(action: () => Promise<unknown>) {
    setLoading(true);
    setError(null);
    try {
      await action();
      router.push(searchParams.get("next") || "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void finishLogin(() => login(email, password));
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <label htmlFor="email" className="text-sm font-semibold text-slate-800">
          Email
        </label>
        <input
          suppressHydrationWarning
          id="email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="field mt-2 w-full"
          placeholder="you@example.com"
        />
      </div>
      <div>
        <div className="flex items-center justify-between">
          <label htmlFor="password" className="text-sm font-semibold text-slate-800">
            Password
          </label>
          <Link href="/login" className="text-sm font-semibold text-primary-hover hover:text-primary">
            Forgot password?
          </Link>
        </div>
        <input
          suppressHydrationWarning
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="field mt-2 w-full"
          placeholder="Enter your password"
        />
      </div>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      <button
        suppressHydrationWarning
        type="submit"
        disabled={loading}
        className="btn-primary w-full"
      >
        {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
        Login
        {!loading ? <ArrowRight className="h-4 w-4" /> : null}
      </button>
      <button
        suppressHydrationWarning
        type="button"
        disabled={loading}
        onClick={() => void finishLogin(loginWithDemoAccount)}
        className="btn-secondary w-full"
      >
        Continue with demo workspace
      </button>
      <p className="text-center text-sm text-slate-600">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="font-semibold text-slate-900">
          Sign up
        </Link>
      </p>
    </form>
  );
}
