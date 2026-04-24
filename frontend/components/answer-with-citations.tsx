"use client";

import { Fragment } from "react";

import { Citation } from "@/types/api";

type AnswerWithCitationsProps = {
  answer: string;
  citations: Citation[];
  onCitationSelect: (citation: Citation) => void;
};

function citationLabel(citation: Citation): string {
  return `Chunk ${citation.chunk_index + 1}${citation.page_number ? `, p. ${citation.page_number}` : ""}`;
}

export function AnswerWithCitations({
  answer,
  citations,
  onCitationSelect,
}: AnswerWithCitationsProps) {
  const citationsByChunkId = new Map(citations.map((citation) => [citation.chunk_id, citation]));
  const segments = answer.split(/(\[chunk:\d+\])/g);

  return (
    <p className="mt-5 whitespace-pre-wrap text-sm leading-8 text-slate-700">
      {segments.map((segment, index) => {
        const match = segment.match(/^\[chunk:(\d+)\]$/);
        if (!match) {
          return <Fragment key={`${segment}-${index}`}>{segment}</Fragment>;
        }

        const chunkId = Number(match[1]);
        const citation = citationsByChunkId.get(chunkId);
        if (!citation) {
          return <Fragment key={`${segment}-${index}`}>{segment}</Fragment>;
        }

        return (
          <button
            key={`${segment}-${index}`}
            type="button"
            onClick={() => onCitationSelect(citation)}
            className="mx-1 inline-flex translate-y-[-1px] items-center rounded-full border border-primary/20 bg-primary-soft px-2.5 py-0.5 align-middle text-xs font-semibold text-primary-hover transition hover:border-primary/40 hover:bg-white"
            aria-label={`Open evidence for ${citation.document_title}, ${citationLabel(citation)}`}
          >
            {citationLabel(citation)}
          </button>
        );
      })}
    </p>
  );
}
