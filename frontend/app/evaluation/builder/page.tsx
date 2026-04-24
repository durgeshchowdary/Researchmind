"use client";

import { FormEvent, useEffect, useState } from "react";

import { addEvalQuestion, createEvalSet, fetchEvalSets, runEvalSet } from "@/lib/api";
import { EvalRunPublic, EvalSetPublic } from "@/types/api";
import { selectedWorkspaceId } from "@/components/workspace-switcher";


export default function EvaluationBuilderPage() {
  const [sets, setSets] = useState<EvalSetPublic[]>([]);
  const [active, setActive] = useState<EvalSetPublic | null>(null);
  const [run, setRun] = useState<EvalRunPublic | null>(null);
  const [name, setName] = useState("");
  const [question, setQuestion] = useState("");
  const [terms, setTerms] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const data = await fetchEvalSets(selectedWorkspaceId());
    setSets(data);
    setActive(data[0] ?? null);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Could not load benchmark sets."));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    await createEvalSet(name, "", selectedWorkspaceId());
    setName("");
    await load();
  }

  async function onAddQuestion(event: FormEvent) {
    event.preventDefault();
    if (!active) return;
    const updated = await addEvalQuestion(active.id, question, terms.split(",").map((term) => term.trim()).filter(Boolean));
    setActive(updated);
    setSets((items) => items.map((item) => item.id === updated.id ? updated : item));
    setQuestion("");
    setTerms("");
  }

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <p className="section-eyebrow">Benchmarks</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Dataset builder</h1>
        <p className="mt-2 text-sm text-slate-300">Create workspace-specific evaluation sets and run groundedness checks.</p>
      </section>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="app-card p-5">
          <h2 className="text-lg font-semibold text-slate-950">Evaluation sets</h2>
          <form onSubmit={onCreate} className="mt-3 flex gap-2">
            <input className="field" value={name} onChange={(event) => setName(event.target.value)} placeholder="Set name" />
            <button className="btn-primary" type="submit">Create</button>
          </form>
          <div className="mt-4 space-y-2">
            {sets.map((set) => (
              <button key={set.id} type="button" onClick={() => setActive(set)} className="interactive-card w-full p-3 text-left">
                <p className="font-semibold text-slate-950">{set.name}</p>
                <p className="text-xs text-slate-500">{set.questions.length} question(s)</p>
              </button>
            ))}
          </div>
        </div>
        <div className="app-card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-950">{active?.name ?? "No set selected"}</h2>
            {active ? <button type="button" className="btn-primary" onClick={() => runEvalSet(active.id).then(setRun)}>Run</button> : null}
          </div>
          {active ? (
            <form onSubmit={onAddQuestion} className="mt-4 grid gap-2 md:grid-cols-[1fr_1fr_auto]">
              <input className="field" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Question" />
              <input className="field" value={terms} onChange={(event) => setTerms(event.target.value)} placeholder="Expected terms, comma separated" />
              <button className="btn-secondary" type="submit">Add</button>
            </form>
          ) : null}
          <div className="mt-4 space-y-2">
            {active?.questions.map((item) => (
              <div key={item.id} className="rounded-xl border border-slate-200 bg-white p-3">
                <p className="font-medium text-slate-900">{item.question}</p>
                <p className="text-xs text-slate-500">{item.expected_terms.join(", ") || "No expected terms"}</p>
              </div>
            ))}
          </div>
          {run ? (
            <div className="mt-5 rounded-xl border border-emerald/20 bg-emerald/10 p-4 text-sm text-emerald">
              Groundedness {Math.round(run.summary.groundedness_score * 100)}% - Recall {Math.round(run.summary.top_k_recall * 100)}%
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
