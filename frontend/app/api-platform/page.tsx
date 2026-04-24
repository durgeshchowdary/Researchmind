"use client";

import { FormEvent, useEffect, useState } from "react";

import { createApiKey, deleteApiKey, fetchApiKeys } from "@/lib/api";
import { ApiKeyPublic } from "@/types/api";
import { selectedWorkspaceId } from "@/components/workspace-switcher";


export default function ApiPlatformPage() {
  const [keys, setKeys] = useState<ApiKeyPublic[]>([]);
  const [created, setCreated] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setKeys(await fetchApiKeys(selectedWorkspaceId()));
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Could not load API keys."));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    const key = await createApiKey(name, selectedWorkspaceId());
    setCreated(key.api_key);
    setName("");
    await load();
  }

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <p className="section-eyebrow">API Platform</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Scoped retrieval APIs</h1>
      </section>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <div className="app-card p-5">
          <form onSubmit={onCreate} className="flex gap-2">
            <input className="field" value={name} onChange={(event) => setName(event.target.value)} placeholder="Key name" />
            <button className="btn-primary" type="submit">Create key</button>
          </form>
          {created ? <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">New key: {created}</p> : null}
          <div className="mt-4 space-y-2">
            {keys.map((key) => (
              <div key={key.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3 text-sm">
                <span>{key.name} - {key.prefix}</span>
                <button className="btn-secondary px-3 py-1" type="button" onClick={() => deleteApiKey(key.id).then(load)}>Delete</button>
              </div>
            ))}
          </div>
        </div>
        <pre className="app-card overflow-x-auto p-5 text-xs text-slate-700">{`curl -X POST http://localhost:8000/api/retrieve \\
  -H "X-API-Key: rm_..." \\
  -H "Content-Type: application/json" \\
  -d '{"query":"hybrid retrieval","limit":5}'`}</pre>
      </section>
    </div>
  );
}
