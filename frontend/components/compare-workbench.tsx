"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowRight, FileSearch, GitCompareArrows, ShieldCheck } from "lucide-react";

import { compareDocuments, fetchDocuments } from "@/lib/api";
import { Citation, CompareResponse, ComparisonPoint, DocumentSummary } from "@/types/api";
import { EvidenceModal } from "./evidence-modal";


const STRENGTH_STYLES = {
  strong: "bg-emerald/10 text-emerald border-emerald/20",
  medium: "bg-amber/10 text-amber border-amber/20",
  weak: "bg-orange-50 text-orange-700 border-orange-200",
  insufficient: "bg-rose-50 text-rose-700 border-rose-200",
} as const;

const POINT_STYLES = {
  agreement: "border-emerald/20 bg-emerald/10 text-emerald",
  difference: "border-cyan/20 bg-cyan/10 text-cyan",
  unique: "border-violet/20 bg-violet/10 text-violet",
} as const;

export function CompareWorkbench() {
  const searchParams = useSearchParams();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  useEffect(() => {
    fetchDocuments()
      .then((data) => {
        setDocuments(data);
        const initialId = Number(searchParams.get("documentId"));
        if (Number.isFinite(initialId) && data.some((document) => document.id === initialId)) {
          setSelectedIds([initialId]);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load documents."));
  }, [searchParams]);

  const citationByChunkId = useMemo(() => {
    return new Map(response?.citations.map((citation) => [citation.chunk_id, citation]) ?? []);
  }, [response?.citations]);

  function toggleDocument(documentId: number) {
    setSelectedIds((current) => {
      if (current.includes(documentId)) {
        return current.filter((id) => id !== documentId);
      }
      return [...current, documentId].slice(0, 4);
    });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (selectedIds.length < 2) {
      setError("Select at least two documents to compare.");
      return;
    }
    if (selectedIds.length > 4) {
      setError("Compare up to four documents at a time.");
      return;
    }

    setLoading(true);
    setError(null);
    setSelectedCitation(null);
    try {
      setResponse(await compareDocuments(selectedIds, question));
    } catch (err) {
      setResponse(null);
      setError(err instanceof Error ? err.message : "Could not compare documents.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <form onSubmit={onSubmit} className="app-card p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-cyan text-white shadow-lg shadow-primary/20">
              <GitCompareArrows className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-xl font-semibold text-slate-950">Compare documents</h1>
              <p className="mt-1 text-sm text-slate-600">
                Compare documents to find agreements, differences, and unique points.
              </p>
            </div>
          </div>

          <div className="mt-5">
            <label htmlFor="comparison-question" className="text-sm font-medium text-slate-700">
              Comparison question
            </label>
            <textarea
              id="comparison-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Optional: compare methods, findings, risks, datasets..."
              className="mt-2 min-h-28 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10"
            />
          </div>

          <div className="mt-5">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-slate-700">Documents</p>
              <span className="rounded-full bg-primary-soft px-3 py-1 text-xs font-semibold text-primary-hover">
                {selectedIds.length}/4 selected
              </span>
            </div>
            <div className="mt-3 grid gap-2">
              {documents.length ? (
                documents.map((document) => {
                  const selected = selectedIds.includes(document.id);
                  return (
                    <button
                      key={document.id}
                      type="button"
                      onClick={() => toggleDocument(document.id)}
                      className={`rounded-2xl border p-4 text-left transition ${
                        selected
                          ? "border-primary/40 bg-primary-soft shadow-lg shadow-primary/10"
                          : "border-slate-200 bg-white hover:border-primary/30 hover:bg-slate-50"
                      }`}
                    >
                      <p className="font-medium text-slate-950">{document.title}</p>
                      <p className="mt-1 text-sm text-slate-500">
                        {document.chunk_count} chunks - {document.status}
                      </p>
                    </button>
                  );
                })
              ) : (
                <p className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-4 text-sm text-slate-600">
                  No documents yet. Upload at least two documents to start comparing.
                </p>
              )}
            </div>
          </div>

          <button type="submit" disabled={loading || selectedIds.length < 2} className="btn-primary mt-5">
            {loading ? "Comparing documents..." : "Compare documents"}
            <ArrowRight className="h-4 w-4" />
          </button>

          {error ? <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
        </form>

        <section className="app-card p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">Comparison result</h2>
              <p className="mt-1 text-sm text-slate-600">Grounded synthesis with cited supporting chunks.</p>
            </div>
            {response ? (
              <span className={`rounded-md border px-3 py-1 text-xs font-semibold ${STRENGTH_STYLES[response.evidence_strength]}`}>
                {response.evidence_strength} evidence - {response.evidence_score}/100
              </span>
            ) : null}
          </div>

          {loading ? (
            <div className="mt-5 space-y-3">
              <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
              <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
              <p className="text-sm text-slate-500">Searching selected documents...</p>
            </div>
          ) : response ? (
            <div className="mt-5 space-y-5">
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <p className="text-sm leading-7 text-slate-700">{response.comparison_summary}</p>
              </div>
              <EvidenceQuality response={response} />
              <PointGroup title="Agreements" points={response.agreements} citationByChunkId={citationByChunkId} onOpen={setSelectedCitation} />
              <PointGroup title="Differences" points={response.differences} citationByChunkId={citationByChunkId} onOpen={setSelectedCitation} />
              <PointGroup title="Unique points" points={response.unique_points} citationByChunkId={citationByChunkId} onOpen={setSelectedCitation} />
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-5">
              <FileSearch className="h-6 w-6 text-primary" />
              <h3 className="mt-3 font-semibold text-slate-950">Your comparison will appear here</h3>
              <p className="mt-2 text-sm text-slate-600">Select two to four documents and run a comparison.</p>
            </div>
          )}
        </section>
      </div>

      {response?.citations.length ? (
        <section className="mt-5 app-card p-5">
          <h2 className="text-lg font-semibold text-slate-950">Citations</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {response.citations.map((citation) => (
              <button
                key={citation.chunk_id}
                type="button"
                onClick={() => setSelectedCitation(citation)}
                className="interactive-card p-4 text-left"
              >
                <p className="font-medium text-slate-950">{citation.document_title}</p>
                <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">{citation.chunk_text_snippet}</p>
              </button>
            ))}
          </div>
        </section>
      ) : null}

      <EvidenceModal citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </>
  );
}

function EvidenceQuality({ response }: { response: CompareResponse }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-slate-950">Evidence quality</h3>
      </div>
      <div className="mt-3 grid gap-2">
        {response.evidence_reasons.map((reason) => (
          <p key={reason} className="rounded-xl bg-emerald/10 px-3 py-2 text-sm text-emerald">
            {reason}
          </p>
        ))}
        {response.evidence_warnings.concat(response.warnings).map((warning) => (
          <p key={warning} className="rounded-xl bg-amber/10 px-3 py-2 text-sm text-amber">
            {warning}
          </p>
        ))}
      </div>
    </div>
  );
}

function PointGroup({
  title,
  points,
  citationByChunkId,
  onOpen,
}: {
  title: string;
  points: ComparisonPoint[];
  citationByChunkId: Map<number, Citation>;
  onOpen: (citation: Citation) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-500">{title}</h3>
      <div className="mt-3 grid gap-3">
        {points.length ? (
          points.map((point, index) => (
            <div key={`${point.type}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="max-w-3xl text-sm leading-6 text-slate-800">{point.text}</p>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${POINT_STYLES[point.type]}`}>
                  {point.confidence}% confidence
                </span>
              </div>
              {point.supporting_chunk_ids.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {point.supporting_chunk_ids.map((chunkId) => {
                    const citation = citationByChunkId.get(chunkId);
                    return (
                      <button
                        key={chunkId}
                        type="button"
                        onClick={() => citation && onOpen(citation)}
                        disabled={!citation}
                        className="rounded-full border border-primary/20 bg-primary-soft px-3 py-1 text-xs font-semibold text-primary-hover transition hover:border-primary/40 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        chunk {chunkId}
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          ))
        ) : (
          <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            Nothing clear enough to report in this category yet.
          </p>
        )}
      </div>
    </div>
  );
}
