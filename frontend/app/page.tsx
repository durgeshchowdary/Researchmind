import Link from "next/link";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  FileSearch,
  Layers3,
  MessageSquareText,
  Search,
  ShieldCheck,
  Upload,
} from "lucide-react";


const steps = [
  { title: "Upload", body: "Add PDFs, notes, papers, or reports.", icon: Upload, color: "from-primary to-violet" },
  { title: "Search", body: "Find exact passages and nearby ideas.", icon: Search, color: "from-cyan to-primary" },
  { title: "Verify", body: "Open the source chunk behind the answer.", icon: ShieldCheck, color: "from-emerald to-cyan" },
];

const features = [
  { title: "Hybrid retrieval", body: "Keyword and semantic search in one focused workflow.", icon: FileSearch, color: "from-primary/20 to-cyan/10" },
  { title: "Grounded answers", body: "Ask questions and keep citations attached.", icon: MessageSquareText, color: "from-pink-500/20 to-primary/10" },
  { title: "Evidence viewer", body: "Inspect chunk text, page metadata, and highlights.", icon: BookOpenCheck, color: "from-cyan/20 to-emerald/10" },
  { title: "Ranking clarity", body: "See why a result appeared without visual noise.", icon: Layers3, color: "from-amber/20 to-pink-500/10" },
];

export default function HomePage() {
  return (
    <div className="bg-transparent">
      <section className="relative overflow-hidden bg-slate-950">
        <div className="color-wash -left-24 top-0 h-80 w-80 bg-primary/35" />
        <div className="color-wash right-0 top-24 h-96 w-96 bg-pink-500/25" />
        <div className="color-wash bottom-0 left-1/2 h-72 w-72 bg-cyan/25" />

        <div className="relative mx-auto grid min-h-[calc(100vh-65px)] max-w-7xl items-center gap-12 px-4 py-16 md:px-6 lg:grid-cols-[1fr_0.92fr]">
          <div>
            <div className="inline-flex rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-cyan">
              ResearchMind
            </div>
            <h1 className="mt-6 max-w-4xl text-6xl font-semibold tracking-tight text-white md:text-7xl">
              Search smarter. <span className="gradient-text">Verify faster.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
              Upload documents, search across them, ask questions, and inspect the exact evidence behind every answer.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/signup" className="btn-primary px-5 py-3">
                Start with a document
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/login" className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/15">
                Try the demo
              </Link>
            </div>
          </div>

          <div className="glass-panel p-3">
            <div className="rounded-[1.35rem] border border-white/10 bg-slate-900/90 p-5">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-gradient-to-br from-primary to-cyan p-3 text-white">
                    <FileSearch className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-semibold text-white">Evidence workspace</p>
                    <p className="text-sm text-slate-400">Research notes.pdf</p>
                  </div>
                </div>
                <span className="rounded-full border border-emerald/20 bg-emerald/10 px-3 py-1 text-xs font-semibold text-emerald">
                  Indexed
                </span>
              </div>
              <div className="mt-5 grid gap-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <p className="text-sm text-slate-400">Question</p>
                  <p className="mt-1 font-semibold text-white">What evidence supports the conclusion?</p>
                </div>
                <div className="rounded-2xl border border-primary/30 bg-primary/15 p-4">
                  <p className="text-sm leading-7 text-slate-200">
                    The answer is grounded in chunk 8 and links directly to the cited source text for review.
                  </p>
                  <button type="button" className="mt-4 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-primary-hover">
                    Open source chunk
                  </button>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  {["12 docs", "186 chunks", "41 citations"].map((item) => (
                    <div key={item} className="rounded-2xl border border-white/10 bg-white/5 p-3 text-sm font-semibold text-slate-200">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="px-4 py-20 md:px-6">
        <div className="mx-auto max-w-7xl">
          <p className="section-eyebrow">How it works</p>
          <h2 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight text-slate-950">
            A fast loop from document to answer to evidence.
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={step.title} className="interactive-card p-6">
                  <div className={`inline-flex rounded-2xl bg-gradient-to-br ${step.color} p-3 text-white shadow-sm`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <p className="mt-5 text-sm font-semibold text-slate-400">0{index + 1}</p>
                  <h3 className="mt-1 text-xl font-semibold text-slate-950">{step.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-600">{step.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="px-4 py-20 md:px-6">
        <div className="mx-auto max-w-7xl">
          <p className="section-eyebrow">Features</p>
          <h2 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight text-slate-950">
            Bold where it helps. Clear where it matters.
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className={`rounded-3xl border border-white/70 bg-gradient-to-br ${feature.color} p-5 shadow-panel`}>
                  <div className="rounded-2xl bg-white p-3 text-primary-hover shadow-sm">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-6 text-lg font-semibold text-slate-950">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-600">{feature.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="px-4 pb-20 md:px-6">
        <div className="mx-auto max-w-7xl overflow-hidden rounded-[2rem] bg-slate-950 p-8 text-white shadow-lift md:p-10">
          <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.16em] text-cyan">Trust layer</p>
              <h2 className="mt-4 text-4xl font-semibold tracking-tight">Answers are only useful when you can check them.</h2>
              <p className="mt-4 text-sm leading-7 text-slate-300">
                ResearchMind keeps citations and source chunks close so users can verify claims before they use them.
              </p>
            </div>
            <div className="grid gap-3">
              {["Citations stay visible in the answer.", "Evidence opens in a source viewer.", "Ranking explanations are readable and compact."].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
                  <CheckCircle2 className="h-5 w-5 text-emerald" />
                  <p className="text-sm text-slate-200">{item}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-8">
            <Link href="/signup" className="btn-primary px-5 py-3">
              Start with a document
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
