"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, BrainCircuit, FileText, Search, Upload } from "lucide-react";

import { fetchDetailedHealth, fetchDocuments, fetchDocumentStats } from "@/lib/api";
import { DocumentSummary, HealthDetailedResponse, StatsSummary } from "@/types/api";
import { StatCard } from "./stat-card";
import { StatusBadge } from "./status-badge";


const quickActions = [
  {
    href: "/upload",
    title: "Upload document",
    body: "Add a PDF, note, report, markdown, or text file.",
    icon: Upload,
  },
  {
    href: "/search",
    title: "Search",
    body: "Find passages across your indexed documents.",
    icon: Search,
  },
  {
    href: "/ask",
    title: "Ask",
    body: "Ask a question and review the source text.",
    icon: BrainCircuit,
  },
];

function formatDate(value: string | null): string {
  if (!value) {
    return "Not available";
  }
  return new Date(value).toLocaleString();
}

export function OverviewDashboard() {
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [health, setHealth] = useState<HealthDetailedResponse | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      try {
        const results = await Promise.allSettled([
          fetchDocumentStats(),
          fetchDetailedHealth(),
          fetchDocuments(),
        ]);
        if (results[0].status === "fulfilled") setStats(results[0].value);
        if (results[1].status === "fulfilled") setHealth(results[1].value);
        if (results[2].status === "fulfilled") setDocuments(results[2].value);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An unexpected error occurred.");
      } finally {
        setLoading(false);
      }
    }
    void loadDashboardData();
  }, []);

  const recentDocuments = documents.slice(0, 5);

  return (
    <div className="space-y-6">
      <section className="hero-surface rounded-[1.75rem] border border-white/70 p-6 shadow-panel md:p-8">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <p className="section-eyebrow">Dashboard</p>
            <h1 className="mt-2 text-4xl font-semibold tracking-tight text-white">Your documents</h1>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-300">
              Start from recent files, upload something new, or search across your library.
            </p>
          </div>
          <Link href="/upload" className="btn-primary">
            Upload document
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Documents"
          value={loading ? "..." : stats?.document_count ?? 0}
          note="Files in your library."
        />
        <StatCard
          label="Chunks"
          value={loading ? "..." : stats?.chunk_count ?? 0}
          note="Searchable text sections."
        />
        <StatCard
          label="Indexed"
          value={loading ? "..." : stats?.indexed_document_count ?? 0}
          note="Ready for search."
        />
        <StatCard
          label="Last indexed"
          value={loading ? "..." : formatDate(stats?.last_indexed_at ?? null)}
          note="Most recent processing run."
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="app-card p-5">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">Recently added</h2>
              <p className="mt-1 text-sm text-slate-600">The latest documents in your workspace.</p>
            </div>
            <Link href="/documents" className="btn-secondary">
              View all
            </Link>
          </div>

          <div className="mt-5 space-y-3">
            {loading ? (
              <p className="muted-panel text-sm text-slate-600">Loading documents...</p>
            ) : recentDocuments.length ? (
              recentDocuments.map((document) => (
                <div key={document.id} className="interactive-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <FileText className="h-4 w-4 text-slate-500" />
                      <p className="truncate font-semibold text-slate-950">{document.title}</p>
                      <StatusBadge status={document.status} />
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                      {document.file_name} - {document.chunk_count} chunks - {formatDate(document.uploaded_at)}
                    </p>
                  </div>
                  <Link href={`/ask?documentId=${document.id}`} className="btn-secondary shrink-0">
                    Ask
                  </Link>
                </div>
              ))
            ) : (
              <div className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-6">
                <h3 className="font-semibold text-slate-950">No documents yet</h3>
                <p className="mt-2 text-sm text-slate-600">Your library is ready when you are. Upload one to start searching.</p>
                <Link href="/upload" className="btn-primary mt-4">
                  Upload document
                </Link>
              </div>
            )}
          </div>
        </div>

        <div className="app-card p-5">
          <h2 className="text-lg font-semibold text-slate-950">Quick actions</h2>
          <div className="mt-4 space-y-3">
            {quickActions.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} className="interactive-card block p-4">
                  <div className="flex items-start gap-3">
                    <Icon className="mt-0.5 h-5 w-5 text-primary-hover" />
                    <div>
                      <p className="font-semibold text-slate-950">{item.title}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{item.body}</p>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <section className="app-card p-5 text-sm">
        <h2 className="text-lg font-semibold text-slate-950">System status</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <p className="muted-panel">
            Backend:{" "}
            <span className="font-semibold text-slate-950">
              {loading ? "..." : health?.status === "ok" ? "Ready" : "Unavailable"}
            </span>
          </p>
          <p className="muted-panel">
            Database:{" "}
            <span className="font-semibold text-slate-950">
              {loading ? "..." : health?.database_ready ? "Ready" : "Missing"}
            </span>
          </p>
          <p className="muted-panel">
            Keyword index:{" "}
            <span className="font-semibold text-slate-950">
              {loading ? "..." : health?.bm25_ready ? "Ready" : "Pending"}
            </span>
          </p>
          <p className="muted-panel">
            Semantic index:{" "}
            <span className="font-semibold text-slate-950">
              {loading ? "..." : health?.semantic_search_ready ? "Ready" : "Pending"}
            </span>
          </p>
        </div>
      </section>
    </div>
  );
}
