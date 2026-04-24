"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BrainCircuit, Clock3, FileText, GitCompareArrows, Layers3, Lightbulb, Sparkles } from "lucide-react";

import { fetchDocuments } from "@/lib/api";
import { DocumentSummary } from "@/types/api";
import { StatusBadge } from "./status-badge";


export function DocumentsTable() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchDocuments();
        setDocuments(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load documents");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  if (loading) {
    return <p className="muted-panel text-sm text-slate-600">Loading documents...</p>;
  }

  if (error) {
    return <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p>;
  }

  if (!documents.length) {
    return (
      <div className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-6">
        <h3 className="font-semibold text-slate-950">No documents yet</h3>
        <p className="mt-2 text-sm text-slate-600">Drop a PDF, note, or report to build your searchable workspace.</p>
        <Link href="/upload" className="btn-primary mt-4">
          Upload document
        </Link>
      </div>
    );
  }

  const indexedCount = documents.filter((document) => document.status === "indexed").length;
  const totalChunks = documents.reduce((sum, document) => sum + document.chunk_count, 0);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="app-card p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-primary-soft p-2.5 text-primary-hover">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Documents</p>
              <p className="text-2xl font-semibold text-slate-900">{documents.length}</p>
            </div>
          </div>
        </div>
        <div className="app-card p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-emerald/10 p-2.5 text-emerald">
              <Layers3 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Chunks</p>
              <p className="text-2xl font-semibold text-slate-900">{totalChunks}</p>
            </div>
          </div>
        </div>
        <div className="app-card p-4">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-amber/10 p-2.5 text-amber">
              <Clock3 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-slate-500">Ready for search</p>
              <p className="text-2xl font-semibold text-slate-900">{indexedCount}</p>
            </div>
          </div>
        </div>
      </div>
      <div className="grid gap-4">
        {documents.map((document) => (
          <article key={document.id} className="interactive-card p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={document.status} />
                    <span className="badge bg-slate-50">
                    {document.file_type.toUpperCase()}
                  </span>
                  {document.year ? (
                    <span className="badge bg-primary-soft text-primary-hover">
                      {document.year}
                    </span>
                  ) : null}
                </div>
                <h3 className="mt-3 text-xl font-semibold text-slate-950">{document.title}</h3>
                <p className="mt-1 text-sm text-slate-500">{document.file_name}</p>
                {document.authors.length ? (
                  <p className="mt-2 text-sm text-slate-700">{document.authors.join(", ")}</p>
                ) : (
                  <p className="mt-2 text-sm text-slate-500">Authors not detected</p>
                )}
                {document.abstract ? (
                  <p className="mt-3 line-clamp-3 max-w-3xl text-sm leading-6 text-slate-600">{document.abstract}</p>
                ) : (
                  <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">
                    Abstract metadata was not detected automatically. The paper is still searchable from extracted text.
                  </p>
                )}
                {document.keywords.length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {document.keywords.slice(0, 8).map((keyword) => (
                    <span key={keyword} className="rounded-full bg-primary-soft px-2.5 py-1 text-xs font-medium text-primary-hover">
                        {keyword}
                      </span>
                    ))}
                  </div>
                ) : null}
                {document.status_message ? (
                  <p className="mt-3 text-xs leading-5 text-slate-500">{document.status_message}</p>
                ) : null}
                {document.error_message ? (
                  <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-700">{document.error_message}</p>
                ) : null}
                {document.status !== "indexed" ? (
                  <div className="mt-3 max-w-md">
                    <div className="flex justify-between text-xs font-medium text-slate-500">
                      <span>Indexing progress</span>
                      <span>{document.progress}%</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(document.progress, 6)}%` }} />
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="grid shrink-0 grid-cols-2 gap-2 text-sm sm:grid-cols-4 lg:w-96 lg:grid-cols-2">
                <Link href={`/ask?documentId=${document.id}`} className="btn-primary px-3 py-2">
                  <BrainCircuit className="h-4 w-4" />
                  Ask
                </Link>
                <Link href={`/summarizer?documentId=${document.id}`} className="btn-secondary px-3 py-2">
                  <Sparkles className="h-4 w-4" />
                  Summarize
                </Link>
                <Link href={`/compare?documentId=${document.id}`} className="btn-secondary px-3 py-2">
                  <GitCompareArrows className="h-4 w-4" />
                  Compare
                </Link>
                <Link href={`/gap-finder?documentId=${document.id}`} className="btn-secondary px-3 py-2">
                  <Lightbulb className="h-4 w-4" />
                  Gaps
                </Link>
              </div>
            </div>
            <div className="mt-5 grid gap-3 border-t border-slate-100 pt-4 text-sm text-slate-600 sm:grid-cols-4">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Pages</p>
                <p className="mt-1 font-semibold text-slate-900">{document.page_count ?? "-"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Chunks</p>
                <p className="mt-1 font-semibold text-slate-900">{document.chunk_count}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Uploaded</p>
                <p className="mt-1 font-semibold text-slate-900">{new Date(document.uploaded_at).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-slate-400">Indexed</p>
                <p className="mt-1 font-semibold text-slate-900">
                  {document.last_indexed_at ? new Date(document.last_indexed_at).toLocaleDateString() : "Pending"}
                </p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
