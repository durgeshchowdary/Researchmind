"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowRight, FileText, ShieldCheck } from "lucide-react";

import { askResearchMind, fetchDocuments } from "@/lib/api";
import { AskResponse, Citation, DocumentSummary } from "@/types/api";
import { AnswerWithCitations } from "./answer-with-citations";
import { EvidenceModal } from "./evidence-modal";
import { SearchResultCard } from "./search-result-card";


const STRENGTH_STYLES = {
  strong: "bg-emerald/10 text-emerald border-emerald/20",
  medium: "bg-amber/10 text-amber border-amber/20",
  weak: "bg-orange-50 text-orange-700 border-orange-200",
  insufficient: "bg-rose-50 text-rose-700 border-rose-200",
} as const;

const CLAIM_STYLES = {
  supported: "bg-emerald/10 text-emerald border-emerald/20",
  partially_supported: "bg-amber/10 text-amber border-amber/20",
  unsupported: "bg-rose-50 text-rose-700 border-rose-200",
} as const;

export function AskWorkbench() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | undefined>(undefined);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  useEffect(() => {
    fetchDocuments()
      .then((data) => {
        setDocuments(data);
        const documentId = Number(new URLSearchParams(globalThis.location.search).get("documentId"));
        if (Number.isFinite(documentId) && data.some((document) => document.id === documentId)) {
          setSelectedDocumentId(documentId);
        }
      })
      .catch((err) => {
        setDocuments([]);
        setDocumentsError(err instanceof Error ? err.message : "Could not load documents.");
      });
  }, []);

  useEffect(() => {
    if (!selectedCitation || !response) {
      return;
    }

    const citationStillPresent = response.citations.some((citation) => citation.chunk_id === selectedCitation.chunk_id);
    if (!citationStillPresent) {
      setSelectedCitation(null);
    }
  }, [response, selectedCitation]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setError("Enter a question.");
      setResponse(null);
      setSelectedCitation(null);
      return;
    }

    setLoading(true);
    setError(null);
    setSelectedCitation(null);
    try {
      setResponse(await askResearchMind(trimmedQuestion, 6, selectedDocumentId));
    } catch (err) {
      setResponse(null);
      setError(err instanceof Error ? err.message : "Could not generate an answer.");
    } finally {
      setLoading(false);
    }
  }

  const answerSourceLabel = useMemo(() => {
    switch (response?.answer_source) {
      case "llm":
        return "Generated answer";
      case "extractive_fallback":
        return "Source text answer";
      case "insufficient_evidence":
        return "Not enough evidence";
      default:
        return "No answer yet";
    }
  }, [response?.answer_source]);

  const citationByChunkId = useMemo(() => {
    return new Map(response?.citations.map((citation) => [citation.chunk_id, citation]) ?? []);
  }, [response?.citations]);

  return (
    <>
      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <form onSubmit={onSubmit} className="app-card p-5">
          <div>
            <label htmlFor="ask-document" className="text-sm font-medium text-slate-700">
              Document
            </label>
            <select
              id="ask-document"
              className="field mt-2 w-full"
              value={selectedDocumentId ?? ""}
              onChange={(event) =>
                setSelectedDocumentId(event.target.value ? Number(event.target.value) : undefined)
              }
            >
              <option value="">Search across all documents</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.title}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-4">
            <label htmlFor="question" className="text-sm font-medium text-slate-700">
              Question
            </label>
            <textarea
              id="question"
              className="mt-2 min-h-48 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-primary/10"
              placeholder="Ask a question about your documents..."
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </div>

          <button type="submit" disabled={loading} className="btn-primary mt-4">
            {loading ? "Generating answer..." : "Ask question"}
            <ArrowRight className="h-4 w-4" />
          </button>

          {error ? <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p> : null}
          {documentsError ? <p className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">{documentsError}</p> : null}
          {!documents.length && !documentsError ? (
            <p className="mt-4 rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-4 text-sm text-slate-600">
              Ask a question after uploading documents.
            </p>
          ) : null}
        </form>

        <section className="app-card p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">Answer</h2>
              <p className="mt-1 text-sm text-slate-600">Citations appear inline when the answer is ready.</p>
            </div>
            {response ? (
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-primary/20 bg-primary-soft px-3 py-1 text-xs font-semibold text-primary-hover">
                  {answerSourceLabel}
                </span>
                <span className={`rounded-md border px-3 py-1 text-xs font-semibold ${STRENGTH_STYLES[response.evidence_strength]}`}>
                  {response.evidence_strength} evidence - {response.evidence_score}/100
                </span>
              </div>
            ) : null}
          </div>

          {loading ? (
            <div className="mt-5 space-y-3">
              <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
              <div className="h-4 w-full animate-pulse rounded bg-slate-100" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-slate-100" />
              <p className="text-sm text-slate-500">Searching your documents...</p>
            </div>
          ) : response ? (
            <AnswerWithCitations
              answer={response.answer}
              citations={response.citations}
              onCitationSelect={setSelectedCitation}
            />
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-5">
              <h3 className="font-semibold text-slate-950">No answer yet</h3>
              <p className="mt-2 text-sm text-slate-600">Ask a question after uploading documents.</p>
            </div>
          )}

          {response?.warnings.map((warning) => (
            <p key={warning} className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              {warning}
            </p>
          ))}

          {response ? (
            <details className="mt-5 rounded-2xl border border-slate-200 bg-white/80 p-4 shadow-sm" open>
              <summary className="cursor-pointer text-sm font-semibold text-slate-950">
                Evidence quality
              </summary>
              <p className="mt-2 text-sm text-slate-600">
                ResearchMind checks whether each answer is backed by retrieved evidence.
              </p>
              <div className="mt-4 grid gap-2">
                {response.evidence_reasons.map((reason) => (
                  <p key={reason} className="rounded-xl bg-emerald/10 px-3 py-2 text-sm text-emerald">
                    {reason}
                  </p>
                ))}
                {response.evidence_warnings.map((warning) => (
                  <p key={warning} className="rounded-xl bg-amber/10 px-3 py-2 text-sm text-amber">
                    {warning}
                  </p>
                ))}
              </div>
            </details>
          ) : null}
        </section>
      </div>

      {response ? (
        <section className="mt-5 app-card p-5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary" />
            <h2 className="text-lg font-semibold text-slate-950">Claim verification</h2>
          </div>
          <p className="mt-1 text-sm text-slate-600">
            Each factual claim is matched against the retrieved supporting chunks.
          </p>
          <div className="mt-4 grid gap-3">
            {response.claim_verifications.length ? (
              response.claim_verifications.map((claim, index) => (
                <div key={`${claim.claim}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <p className="max-w-3xl text-sm font-medium leading-6 text-slate-900">{claim.claim}</p>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${CLAIM_STYLES[claim.status]}`}>
                      {claim.status.replace("_", " ")} - {claim.confidence}%
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{claim.reason}</p>
                  {claim.evidence_chunk_ids.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {claim.evidence_chunk_ids.map((chunkId) => {
                        const citation = citationByChunkId.get(chunkId);
                        return (
                          <button
                            key={chunkId}
                            type="button"
                            onClick={() => citation && setSelectedCitation(citation)}
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
              <p className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-4 text-sm text-slate-600">
                No factual claims were extracted from this answer.
              </p>
            )}
          </div>
        </section>
      ) : null}

      <section className="mt-5 grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="app-card p-5">
          <h2 className="text-lg font-semibold text-slate-950">Citations</h2>
          <p className="mt-1 text-sm text-slate-600">Open a citation to read the supporting text.</p>
          <div className="mt-4 grid gap-3">
            {response?.citations.length ? (
              response.citations.map((citation) => (
                <button
                  key={`${citation.chunk_id}-${citation.chunk_index}`}
                  type="button"
                  onClick={() => setSelectedCitation(citation)}
                  className="interactive-card p-4 text-left"
                >
                  <p className="font-medium text-slate-950">
                    {citation.document_title} - Chunk {citation.chunk_index + 1}
                    {citation.page_number ? ` - Page ${citation.page_number}` : ""}
                  </p>
                  <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">{citation.chunk_text_snippet}</p>
                </button>
              ))
            ) : (
              <p className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-4 text-sm text-slate-600">
                Citations will appear here after an answer is generated.
              </p>
            )}
          </div>
        </div>

        <div className="app-card p-5">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-slate-600" />
            <h2 className="text-lg font-semibold text-slate-950">Supporting text</h2>
          </div>
          <p className="mt-1 text-sm text-slate-600">Retrieved chunks used to prepare the answer.</p>
          <div className="mt-4 grid gap-4">
            {response?.supporting_chunks.length ? (
              response.supporting_chunks.map((chunk) => (
                <SearchResultCard key={chunk.chunk_id} result={chunk} compact />
              ))
            ) : (
              <p className="rounded-2xl border border-dashed border-primary/30 bg-primary-soft/60 p-4 text-sm text-slate-600">
                Supporting evidence will show up here once a question is answered.
              </p>
            )}
          </div>
        </div>
      </section>

      <EvidenceModal citation={selectedCitation} onClose={() => setSelectedCitation(null)} />
    </>
  );
}
