import { FileSearch, MessageSquareText, Upload } from "lucide-react";

import { SignupForm } from "@/components/signup-form";


export default function SignupPage() {
  return (
    <main className="px-4 py-12 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-160px)] max-w-6xl items-center gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <section className="hero-surface rounded-[1.75rem] border border-white/70 p-8 shadow-panel">
          <p className="section-eyebrow">Create workspace</p>
          <h1 className="mt-4 max-w-xl text-4xl font-semibold tracking-tight text-white md:text-5xl">
            Create your ResearchMind workspace.
          </h1>
          <p className="mt-4 max-w-lg text-sm leading-7 text-slate-300">
            Add documents, search across them, and keep supporting evidence close to every answer.
          </p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {[
              { label: "Upload", icon: Upload },
              { label: "Search", icon: FileSearch },
              { label: "Ask", icon: MessageSquareText },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="rounded-2xl border border-white/10 bg-white/10 p-5 shadow-sm backdrop-blur">
                  <Icon className="h-5 w-5 text-cyan" />
                  <p className="mt-4 font-semibold text-white">{item.label}</p>
                </div>
              );
            })}
          </div>
        </section>

        <section className="app-card p-6 md:p-8">
          <p className="section-eyebrow">Sign up</p>
          <h2 className="mt-3 text-2xl font-semibold text-slate-950">Start with your first document</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Create an account to save your document workspace.</p>
          <div className="mt-7">
            <SignupForm />
          </div>
        </section>
      </div>
    </main>
  );
}
