"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import { renderEvidenceHtml } from "@/lib/rich-text";
import { SearchResult } from "@/types/api";

export function SearchResultCard({
  result,
  compact = false,
}: {
  result: SearchResult;
  compact?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const safeHtml = renderEvidenceHtml(result.highlighted_snippet);

  return (
    <article className={`app-card ${compact ? "p-4" : "p-5"}`}>
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary-hover">
            {result.retrieval_mode}
          </p>
          <h3 className={`${compact ? "text-base" : "text-lg"} font-semibold text-slate-900`}>
            {result.document_title}
          </h3>
          <p className="text-sm text-slate-500">
            Chunk {result.chunk_index + 1}
            {result.page_number ? ` | Page ${result.page_number}` : ""}
          </p>
        </div>
        <div className="text-right">
          <div className="rounded-full bg-primary-soft px-3 py-1 text-sm font-semibold text-primary-hover">
            {result.score.toFixed(4)}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            BM25 {result.keyword_score?.toFixed(3) ?? "-"} | Semantic {result.semantic_score?.toFixed(3) ?? "-"}
          </p>
          {result.rerank_score !== null ? (
            <p className="mt-1 text-xs font-semibold text-cyan">Rerank {result.rerank_score.toFixed(3)}</p>
          ) : null}
        </div>
      </div>
      {result.original_rank && result.final_rank && result.original_rank !== result.final_rank ? (
        <p className="mb-3 rounded-xl border border-cyan/20 bg-cyan/10 px-3 py-2 text-xs font-semibold text-cyan">
          Moved {result.final_rank < result.original_rank ? "up" : "down"} after reranking: #{result.original_rank} to #{result.final_rank}
        </p>
      ) : null}
      <p className="text-sm leading-7 text-slate-700" dangerouslySetInnerHTML={{ __html: safeHtml }} />
      {result.matched_terms.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {result.matched_terms.map((term) => (
            <span key={term} className="rounded-full bg-cyan/10 px-2.5 py-1 text-xs font-medium text-cyan">
              {term}
            </span>
          ))}
        </div>
      ) : null}
      <div className="mt-4 rounded-2xl border border-primary/10 bg-primary-soft/50 p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary-hover">Why this result appeared</p>
            <p className="mt-1 text-sm text-slate-700">{result.explanation.summary}</p>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((current) => !current)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-primary/30 hover:text-primary-hover"
          >
            {expanded ? "Less detail" : "More detail"}
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
        {expanded ? (
          <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <p className="font-semibold text-slate-900">Signals</p>
              <div className="mt-2 space-y-2">
                <p>Keyword overlap: {result.explanation.keyword_overlap.length ? result.explanation.keyword_overlap.join(", ") : "none"}</p>
                <p>Title match: {result.explanation.title_match ? "yes" : "no"}</p>
                <p>Semantic similarity: {result.explanation.semantic_match ? "yes" : "no"}</p>
                <p>Original score: {result.score.toFixed(4)}</p>
                <p>Rerank score: {result.rerank_score?.toFixed(4) ?? "not used"}</p>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-3">
              <p className="font-semibold text-slate-900">Score Breakdown</p>
              <ul className="mt-2 space-y-2">
                {result.rerank_reasons.map((line) => (
                  <li key={`rerank-${line}`}>{line}</li>
                ))}
                {result.explanation.score_breakdown.length ? (
                  result.explanation.score_breakdown.map((line) => (
                    <li key={line}>{line}</li>
                  ))
                ) : (
                  <li>No detailed score breakdown was returned for this result.</li>
                )}
              </ul>
            </div>
          </div>
        ) : null}
      </div>
    </article>
  );
}
