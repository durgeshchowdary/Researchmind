"use client";

import { useEffect, useState } from "react";

import { fetchAdminObservability } from "@/lib/api";
import { AdminObservabilityResponse } from "@/types/api";
import { StatCard } from "@/components/stat-card";


export default function ObservabilityPage() {
  const [data, setData] = useState<AdminObservabilityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAdminObservability()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load observability."));
  }, []);

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <p className="section-eyebrow">Observability</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Platform operations</h1>
      </section>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="Search latency" value={`${data?.search_latency_ms ?? 0} ms`} note="Average recorded latency." />
        <StatCard label="Ask latency" value={`${data?.ask_latency_ms ?? 0} ms`} note="Average answer latency." />
        <StatCard label="Index failures" value={data?.failed_indexing_count ?? 0} note="Failed indexing attempts." />
        <StatCard label="Queue mode" value={data?.queue_mode ?? "-"} note={data?.redis_available ? "Redis ready." : "Fallback active."} />
      </section>
      <section className="app-card p-5">
        <h2 className="text-lg font-semibold text-slate-950">System totals</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <p className="muted-panel">Documents: <b>{data?.document_count ?? 0}</b></p>
          <p className="muted-panel">Chunks: <b>{data?.chunk_count ?? 0}</b></p>
          <p className="muted-panel">Evaluation runs: <b>{data?.evaluation_runs ?? 0}</b></p>
        </div>
      </section>
    </div>
  );
}
