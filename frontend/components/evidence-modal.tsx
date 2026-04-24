"use client";

import { MouseEvent, useEffect } from "react";
import { X } from "lucide-react";

import { Citation } from "@/types/api";
import { highlightTermsHtml, renderEvidenceHtml } from "@/lib/rich-text";

export function EvidenceModal({
  citation,
  onClose,
}: {
  citation: Citation | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!citation) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [citation, onClose]);

  if (!citation) {
    return null;
  }

  function handleBackdropClick(event: MouseEvent<HTMLDivElement>) {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4 backdrop-blur-sm"
      onClick={handleBackdropClick}
      role="presentation"
    >
      <div
        className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-[1.5rem] border border-slate-200 bg-white shadow-lift"
        role="dialog"
        aria-modal="true"
        aria-labelledby="evidence-modal-title"
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/10 bg-slate-950 px-6 py-5 text-white">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan">Evidence</p>
            <h3 id="evidence-modal-title" className="mt-2 text-xl font-semibold text-white">
              {citation.document_title}
            </h3>
            <p className="mt-2 text-sm text-slate-300">
              Chunk {citation.chunk_index + 1} | Chunk ID {citation.chunk_id}
              {citation.page_number ? ` | Page ${citation.page_number}` : ""}
            </p>
            {citation.source_url ? (
              <a className="mt-2 inline-block text-sm font-medium text-cyan" href={citation.source_url} target="_blank" rel="noreferrer">
                Open source
              </a>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-white/15 bg-white/10 p-2 text-slate-200 transition hover:bg-white/15"
            aria-label="Close evidence panel"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="max-h-[calc(90vh-96px)] overflow-y-auto px-6 py-6">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary-hover">Why this was cited</p>
              <p className="mt-2 text-sm leading-6 text-slate-700">{citation.explanation_summary}</p>
              {citation.matched_terms.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {citation.matched_terms.map((term) => (
                    <span key={term} className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-primary-hover ring-1 ring-primary/20">
                      {term}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-xs uppercase tracking-[0.14em] text-slate-400">No explicit lexical matches returned</p>
              )}
            </div>
            <div className="rounded-2xl border border-primary/10 bg-primary-soft/60 p-4 md:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Cited snippet</p>
              <p
                className="mt-3 text-sm leading-7 text-slate-700"
                dangerouslySetInnerHTML={{
                  __html: renderEvidenceHtml(citation.highlighted_snippet || citation.chunk_text_snippet),
                }}
              />
            </div>
          </div>
          <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Supporting text</p>
              <p className="text-xs uppercase tracking-[0.14em] text-slate-400">Document: {citation.document_title}</p>
            </div>
            <p
              className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700"
              dangerouslySetInnerHTML={{
                __html: highlightTermsHtml(citation.supporting_chunk_text, citation.matched_terms),
              }}
            />
          </div>
          {(citation.before_context || citation.after_context) ? (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Before context</p>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{citation.before_context ?? "No preceding context returned."}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">After context</p>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{citation.after_context ?? "No following context returned."}</p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
