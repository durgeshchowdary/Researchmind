import { Suspense } from "react";
import { BookOpenCheck, Search, ShieldCheck } from "lucide-react";

import { LoginForm } from "@/components/login-form";


export default function LoginPage() {
  return (
    <main className="px-4 py-12 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-160px)] max-w-6xl items-center gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="hero-surface rounded-[1.75rem] border border-white/70 p-8 shadow-panel">
          <p className="section-eyebrow">Welcome back</p>
          <h1 className="mt-4 max-w-xl text-4xl font-semibold tracking-tight text-white md:text-5xl">
            Continue your research workspace.
          </h1>
          <p className="mt-4 max-w-lg text-sm leading-7 text-slate-300">
            Return to your documents, searches, answers, and evidence trails.
          </p>
          <div className="mt-8 grid gap-3">
            {[
              { title: "Search saved documents", icon: Search },
              { title: "Ask questions with citations", icon: BookOpenCheck },
              { title: "Verify answers from the source", icon: ShieldCheck },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/10 p-4 shadow-sm backdrop-blur">
                  <div className="rounded-xl bg-white p-2.5 text-primary-hover">
                    <Icon className="h-5 w-5" />
                  </div>
                  <p className="font-medium text-white">{item.title}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section className="app-card p-6 md:p-8">
          <p className="section-eyebrow">Login</p>
          <h2 className="mt-3 text-2xl font-semibold text-slate-950">Access ResearchMind</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Use your account or continue with the demo workspace.</p>
          <div className="mt-7">
            <Suspense fallback={<p className="text-sm text-slate-600">Loading login...</p>}>
              <LoginForm />
            </Suspense>
          </div>
        </section>
      </div>
    </main>
  );
}
