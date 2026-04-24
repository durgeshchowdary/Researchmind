"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, LoaderCircle } from "lucide-react";

import { signup } from "@/lib/auth";


export function SignupForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      await signup(name, email, password, confirmPassword);
      setSuccess(true);
      window.setTimeout(() => router.push("/dashboard"), 650);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <div>
        <label htmlFor="name" className="text-sm font-semibold text-slate-800">
          Name
        </label>
        <input
          suppressHydrationWarning
          id="name"
          type="text"
          autoComplete="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="field mt-2 w-full"
          placeholder="Your name"
        />
      </div>
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
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="password" className="text-sm font-semibold text-slate-800">
            Password
          </label>
          <input
            suppressHydrationWarning
            id="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="field mt-2 w-full"
            placeholder="Min. 8 characters"
          />
        </div>
        <div>
          <label htmlFor="confirm-password" className="text-sm font-semibold text-slate-800">
            Confirm password
          </label>
          <input
            suppressHydrationWarning
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="field mt-2 w-full"
            placeholder="Repeat password"
          />
        </div>
      </div>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      {success ? (
        <p className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4" />
          Account created. Opening your workspace...
        </p>
      ) : null}
      <button
        suppressHydrationWarning
        type="submit"
        disabled={loading}
        className="btn-primary w-full"
      >
        {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
        Create account
        {!loading ? <ArrowRight className="h-4 w-4" /> : null}
      </button>
      <p className="text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-slate-900">
          Login
        </Link>
      </p>
    </form>
  );
}
