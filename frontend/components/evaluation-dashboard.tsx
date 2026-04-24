"use client";

import { useEffect, useState } from "react";
import { Activity, Gauge, Play, ShieldCheck, Timer } from "lucide-react";

import { fetchEvaluationSummary, fetchSystemMetrics, runEvaluation } from "@/lib/api";
import { EvaluationRunResponse, EvaluationSummary, SystemMetrics } from "@/types/api";
import { StatCard } from "./stat-card";


function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function EvaluationDashboard() {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [run, setRun] = useState<EvaluationRunResponse | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchEvaluationSummary(), fetchSystemMetrics()])
      .then(([summaryResponse, metricsResponse]) => {
        setSummary(summaryResponse);
        setMetrics(metricsResponse);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load evaluation data."))
      .finally(() => setLoading(false));
  }, []);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const response = await runEvaluation();
      setRun(response);
      setSummary(response.summary);
      setMetrics(await fetchSystemMetrics());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed.");
    } finally {
      setRunning(false);
    }
  }

  const details = run?.results ?? [];

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <p className="section-eyebrow">Evaluation</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Retrieval quality lab</h1>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-300">
              Measure recall, citations, groundedness, unsupported claims, evidence strength, and latency against the current corpus.
            </p>
          </div>
          <button type="button" onClick={handleRun} disabled={running} className="btn-primary">
            <Play className="h-4 w-4" />
            {running ? "Running..." : "Run evaluation"}
          </button>
        </div>
      </section>

      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      {summary?.warnings.map((warning) => (
        <p key={warning} className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{warning}</p>
      ))}

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Groundedness" value={loading ? "..." : percent(summary?.groundedness_score ?? 0)} note="Evidence score adjusted by unsupported claims." />
        <StatCard label="Top-k recall" value={loading ? "..." : percent(summary?.top_k_recall ?? 0)} note="Expected terms and titles found in retrieval." />
        <StatCard label="Citation match" value={loading ? "..." : percent(summary?.citation_match_rate ?? 0)} note="Expected citation chunks returned." />
        <StatCard label="Unsupported claims" value={loading ? "..." : percent(summary?.unsupported_claim_rate ?? 0)} note="Lower is better." />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="app-card p-5">
          <Gauge className="h-5 w-5 text-primary-hover" />
          <p className="mt-3 text-sm text-slate-500">Average evidence score</p>
          <p className="mt-1 text-3xl font-semibold text-slate-950">{Math.round(summary?.average_evidence_score ?? 0)}/100</p>
        </div>
        <div className="app-card p-5">
          <Timer className="h-5 w-5 text-cyan" />
          <p className="mt-3 text-sm text-slate-500">Search / ask latency</p>
          <p className="mt-1 text-3xl font-semibold text-slate-950">
            {Math.round(summary?.average_search_latency_ms ?? metrics?.search_latency_ms ?? 0)} / {Math.round(summary?.average_answer_latency_ms ?? metrics?.ask_latency_ms ?? 0)} ms
          </p>
        </div>
        <div className="app-card p-5">
          <Activity className="h-5 w-5 text-emerald" />
          <p className="mt-3 text-sm text-slate-500">Indexed docs / chunks</p>
          <p className="mt-1 text-3xl font-semibold text-slate-950">
            {metrics?.total_documents_indexed ?? 0} / {metrics?.total_chunks_indexed ?? 0}
          </p>
        </div>
      </section>

      <section className="app-card p-5">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold text-slate-950">Per-question breakdown</h2>
        </div>
        <div className="mt-4 grid gap-3">
          {details.length ? details.map((item) => (
            <article key={item.question} className="rounded-2xl border border-slate-200 bg-white p-4">
              <h3 className="font-semibold text-slate-950">{item.question}</h3>
              <div className="mt-3 grid gap-2 text-sm text-slate-600 md:grid-cols-5">
                <p>Recall: <span className="font-semibold text-slate-950">{percent(item.top_k_recall)}</span></p>
                <p>Citations: <span className="font-semibold text-slate-950">{percent(item.citation_match_rate)}</span></p>
                <p>Unsupported: <span className="font-semibold text-slate-950">{percent(item.unsupported_claim_rate)}</span></p>
                <p>Evidence: <span className="font-semibold text-slate-950">{Math.round(item.average_evidence_score)}/100</span></p>
                <p>Latency: <span className="font-semibold text-slate-950">{Math.round(item.search_latency_ms)} / {Math.round(item.answer_latency_ms)} ms</span></p>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Matched terms: {item.matched_terms.length ? item.matched_terms.join(", ") : "none"}
              </p>
            </article>
          )) : (
            <p className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-4 text-sm text-slate-600">
              Run the benchmark to see per-question retrieval and answer quality.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
