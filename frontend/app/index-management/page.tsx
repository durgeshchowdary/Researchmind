"use client";

import { useEffect, useState } from "react";

import { deleteDocument, fetchDocuments, fetchIndexLogs, fetchIndexStatus, rebuildWorkspaceIndex, reindexDocument } from "@/lib/api";
import { DocumentSummary, IndexLogEntry, IndexStatusResponse } from "@/types/api";
import { StatusBadge } from "@/components/status-badge";
import { selectedWorkspaceId } from "@/components/workspace-switcher";


export default function IndexManagementPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [status, setStatus] = useState<IndexStatusResponse | null>(null);
  const [logs, setLogs] = useState<IndexLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const workspaceId = selectedWorkspaceId();
    setDocuments(await fetchDocuments());
    if (workspaceId) {
      setStatus(await fetchIndexStatus(workspaceId));
      setLogs(await fetchIndexLogs(workspaceId));
    }
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Could not load index management."));
  }, []);

  async function rebuild() {
    const workspaceId = selectedWorkspaceId();
    if (!workspaceId) return;
    setStatus(await rebuildWorkspaceIndex(workspaceId));
    await load();
  }

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <p className="section-eyebrow">Indexes</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Index management</h1>
      </section>
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
      <section className="grid gap-4 md:grid-cols-4">
        <div className="app-card p-4">Docs <b>{status?.document_count ?? documents.length}</b></div>
        <div className="app-card p-4">Chunks <b>{status?.chunk_count ?? 0}</b></div>
        <div className="app-card p-4">Queue <b>{status?.queue_mode ?? "-"}</b></div>
        <button type="button" onClick={rebuild} className="btn-primary">Rebuild workspace</button>
      </section>
      <section className="app-card p-5">
        <h2 className="text-lg font-semibold text-slate-950">Documents</h2>
        <div className="mt-4 space-y-3">
          {documents.map((document) => (
            <div key={document.id} className="interactive-card flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
              <div>
                <div className="flex gap-2"><StatusBadge status={document.status} /><span className="badge">{document.progress}%</span></div>
                <p className="mt-2 font-semibold text-slate-950">{document.title}</p>
                {document.error_message ? <p className="text-sm text-rose-700">{document.error_message}</p> : null}
              </div>
              <div className="flex gap-2">
                <button type="button" className="btn-secondary" onClick={() => reindexDocument(document.id).then(load)}>Reindex</button>
                <button type="button" className="btn-secondary" onClick={() => deleteDocument(document.id).then(load)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="app-card p-5">
        <h2 className="text-lg font-semibold text-slate-950">Index logs</h2>
        <div className="mt-4 space-y-2 text-sm">
          {logs.map((log) => <p key={log.id} className="rounded-xl bg-slate-50 p-3">{log.created_at}: {log.message}</p>)}
        </div>
      </section>
    </div>
  );
}
