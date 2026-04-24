"use client";

import { FormEvent, useEffect, useState } from "react";
import { Search } from "lucide-react";

import { fetchDocuments, runSearch } from "@/lib/api";
import { DocumentSummary, SearchMode, SearchResponse } from "@/types/api";
import { SearchResultCard } from "./search-result-card";


const MODES: SearchMode[] = ["keyword", "semantic", "hybrid"];
const MODE_LABELS: Record<SearchMode, string> = {
  keyword: "Keyword",
  semantic: "Semantic",
  hybrid: "Hybrid",
};

export function SearchWorkbench() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | undefined>(undefined);
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments()
      .then(setDocuments)
      .catch((err) => {
        setDocuments([]);
        setDocumentsError(err instanceof Error ? err.message : "Could not load documents.");
      });
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Enter a search query.");
      setResult(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      setResult(await runSearch(mode, trimmedQuery, 8, selectedDocumentId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <form onSubmit={onSubmit} className="app-card p-5">
        <div className="grid gap-4 lg:grid-cols-[1fr_220px_auto]">
          <div>
            <label htmlFor="search-query" className="text-sm font-medium text-slate-700">
              Search query
            </label>
            <input
              id="search-query"
              className="field mt-2 w-full text-base"
              placeholder="Search your documents..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div>
            <label htmlFor="document-filter" className="text-sm font-medium text-slate-700">
              Document
            </label>
            <select
              id="document-filter"
              className="field mt-2 w-full"
              value={selectedDocumentId ?? ""}
              onChange={(event) =>
                setSelectedDocumentId(event.target.value ? Number(event.target.value) : undefined)
              }
            >
              <option value="">All documents</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.title}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button type="submit" disabled={loading} className="btn-primary w-full lg:w-auto">
              <Search className="h-4 w-4" />
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
        </div>

        <div className="mt-4 inline-flex flex-wrap gap-1 rounded-2xl border border-slate-200 bg-slate-50 p-1">
          {MODES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setMode(item)}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                mode === item
                  ? "bg-white text-primary-hover shadow-sm ring-1 ring-primary/15"
                  : "text-slate-600 hover:bg-white/70 hover:text-slate-950"
              }`}
            >
              {MODE_LABELS[item]}
            </button>
          ))}
        </div>
      </form>

      {error ? (
        <p className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p>
      ) : null}
      {documentsError ? (
        <p className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{documentsError}</p>
      ) : null}

      {result ? (
        <section className="space-y-4">
          <div className="app-card p-4">
            <p className="font-semibold text-slate-950">
              {result.total} result{result.total === 1 ? "" : "s"}
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Showing {MODE_LABELS[mode].toLowerCase()} search for “{result.query}”.
            </p>
          </div>

          {result.warnings.map((warning) => (
            <p key={warning} className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              {warning}
            </p>
          ))}

          {result.results.length ? (
            <div className="grid gap-4">
              {result.results.map((item) => (
                <SearchResultCard key={item.chunk_id} result={item} />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-6">
              <h3 className="font-semibold text-slate-950">No results found</h3>
              <p className="mt-2 text-sm text-slate-600">Try a different query, switch search mode, or search all documents.</p>
            </div>
          )}
        </section>
      ) : (
        <div className="rounded-2xl border border-dashed border-primary/30 bg-white/80 p-6">
          <h3 className="font-semibold text-slate-950">Search your documents</h3>
          <p className="mt-2 text-sm text-slate-600">
            Upload a document first, then search for a phrase, topic, or question.
          </p>
        </div>
      )}
    </div>
  );
}
