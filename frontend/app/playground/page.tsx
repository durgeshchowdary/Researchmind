"use client";

import { FormEvent, useState } from "react";

import { runRetrievalPlayground } from "@/lib/api";
import { RetrievalPipelineName, RetrievalPlaygroundResponse } from "@/types/api";
import { SearchResultCard } from "@/components/search-result-card";
import { selectedWorkspaceId } from "@/components/workspace-switcher";


const pipelines: RetrievalPipelineName[] = ["bm25", "semantic", "hybrid", "hybrid_reranked"];

export default function PlaygroundPage() {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<RetrievalPipelineName[]>(["bm25", "semantic", "hybrid_reranked"]);
  const [response, setResponse] = useState<RetrievalPlaygroundResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setResponse(await runRetrievalPlayground(query, selected, selectedWorkspaceId()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Playground request failed.");
    }
  }

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <p className="section-eyebrow">Playground</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Retrieval pipeline playground</h1>
      </section>
      <form onSubmit={onSubmit} className="app-card grid gap-3 p-5">
        <input className="field" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Compare retrieval strategies..." />
        <div className="flex flex-wrap gap-2">
          {pipelines.map((pipeline) => (
            <label key={pipeline} className="badge cursor-pointer">
              <input
                type="checkbox"
                checked={selected.includes(pipeline)}
                onChange={() => setSelected((items) => items.includes(pipeline) ? items.filter((item) => item !== pipeline) : [...items, pipeline])}
              />
              {pipeline}
            </label>
          ))}
        </div>
        <button className="btn-primary w-fit" type="submit">Run comparison</button>
      </form>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      <section className="grid gap-4 xl:grid-cols-2">
        {response?.pipelines.map((pipeline) => (
          <div key={pipeline.pipeline} className="app-card p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold text-slate-950">{pipeline.pipeline}</h2>
              <span className="badge">{pipeline.latency_ms} ms</span>
            </div>
            {pipeline.warnings.map((warning) => <p key={warning} className="mb-2 text-xs text-amber-700">{warning}</p>)}
            <div className="space-y-3">
              {pipeline.results.map((result) => <SearchResultCard key={`${pipeline.pipeline}-${result.chunk_id}`} result={result} compact />)}
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
