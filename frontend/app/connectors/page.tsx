"use client";

import { FormEvent, useState } from "react";

import { importWebUrl } from "@/lib/api";
import { ConnectorImportResponse } from "@/types/api";
import { selectedWorkspaceId } from "@/components/workspace-switcher";


export default function ConnectorsPage() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<ConnectorImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      setResult(await importWebUrl(url, selectedWorkspaceId()));
      setUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed.");
    }
  }

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <p className="section-eyebrow">Connectors</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Connector hub</h1>
      </section>
      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <form onSubmit={onSubmit} className="app-card p-5">
          <h2 className="text-lg font-semibold text-slate-950">Web URL</h2>
          <input className="field mt-4" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/article" />
          <button className="btn-primary mt-4" type="submit">Import webpage</button>
          {error ? <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
          {result ? <p className="mt-4 rounded-xl border border-emerald/20 bg-emerald/10 p-3 text-sm text-emerald">Imported {result.document.title}</p> : null}
        </form>
        <div className="grid gap-3">
          {["GitHub repo planned", "Notion export planned", "Google Drive planned"].map((title) => (
            <div key={title} className="app-card p-5">
              <p className="font-semibold text-slate-950">{title}</p>
              <p className="mt-1 text-sm text-slate-600">Connector architecture is ready for this source.</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
