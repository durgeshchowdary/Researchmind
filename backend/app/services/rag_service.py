from collections import defaultdict
import time

from app.core.config import get_settings
from app.models.schemas import AskRequest, AskResponse, Citation, EvidenceStrength, SearchRequest, SearchResult, WhyAnswerChunk, WhyAnswerSummary
from app.services.claim_verification_service import claim_verification_service
from app.services.evidence_service import evidence_service
from app.services.llm_client import llm_client
from app.services.observability_service import observability_service
from app.services.search_service import search_service
from app.utils.text import lexical_overlap_score, make_snippet, preprocess_text, sentence_split


settings = get_settings()


class RagService:
    async def answer_question(self, payload: AskRequest, user_id: int | None = None) -> AskResponse:
        started = time.perf_counter()
        retrieval = search_service.hybrid_search(
            SearchRequest(query=payload.question, limit=max(payload.limit * 2, 8), document_id=payload.document_id),
            user_id,
        )
        selected_chunks = self._select_supporting_chunks(retrieval.results, payload.limit)
        if not selected_chunks:
            answer = "I could not find enough evidence for that in the uploaded documents."
            assessment = evidence_service.assess(payload.question, [], [], "insufficient_evidence", answer)
            response = AskResponse(
                answer=answer,
                citations=[],
                retrieval_query=payload.question,
                grounded=False,
                answer_source="insufficient_evidence",
                evidence_strength=assessment.evidence_strength,
                evidence_score=assessment.evidence_score,
                evidence_reasons=assessment.evidence_reasons,
                evidence_warnings=assessment.evidence_warnings,
                claim_verifications=[],
                why_this_answer=WhyAnswerSummary(
                    answer_source="insufficient_evidence",
                    evidence_strength=assessment.evidence_strength,
                    summary="No sufficiently grounded chunks were retrieved for this question.",
                ),
                insufficient_evidence=True,
                warnings=retrieval.warnings,
            )
            observability_service.record_latency("ask", (time.perf_counter() - started) * 1000)
            return response

        citations = [
            Citation(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                document_title=result.document_title,
                chunk_index=result.chunk_index,
                chunk_text_snippet=result.snippet,
                supporting_chunk_text=result.raw_text,
                highlighted_snippet=result.highlighted_snippet,
                matched_terms=result.matched_terms,
                explanation_summary=result.explanation.summary,
                page_number=result.page_number,
                before_context=self._context_before(result.raw_text, result.snippet),
                after_context=self._context_after(result.raw_text, result.snippet),
                source_url=result.source_url,
            )
            for result in selected_chunks
        ]

        insufficient_evidence = self._is_insufficient_evidence(selected_chunks)
        if insufficient_evidence:
            answer = "The available evidence is too weak or incomplete to answer that confidently from the uploaded documents."
            assessment = evidence_service.assess(payload.question, citations, selected_chunks, "insufficient_evidence", answer)
            response = AskResponse(
                answer=answer,
                citations=citations,
                retrieval_query=payload.question,
                grounded=False,
                answer_source="insufficient_evidence",
                evidence_strength=assessment.evidence_strength,
                evidence_score=assessment.evidence_score,
                evidence_reasons=assessment.evidence_reasons,
                evidence_warnings=assessment.evidence_warnings,
                claim_verifications=claim_verification_service.verify(answer, selected_chunks, insufficient_evidence=True),
                why_this_answer=self._why_this_answer("insufficient_evidence", assessment.evidence_strength, selected_chunks),
                insufficient_evidence=True,
                supporting_chunks=selected_chunks,
                warnings=retrieval.warnings,
            )
            observability_service.record_latency("ask", (time.perf_counter() - started) * 1000)
            return response

        prompt = self._build_prompt(payload.question, selected_chunks)
        generated = await llm_client.generate(prompt)
        answer_source = "llm" if generated else "extractive_fallback"
        if not generated:
            generated = self._fallback_answer(payload.question, selected_chunks)

        grounded = "not found" not in generated.lower() and "could not find" not in generated.lower()
        assessment = evidence_service.assess(payload.question, citations, selected_chunks, answer_source, generated)
        response = AskResponse(
            answer=generated,
            citations=citations,
            retrieval_query=payload.question,
            grounded=grounded,
            answer_source=answer_source,
            evidence_strength=assessment.evidence_strength,
            evidence_score=assessment.evidence_score,
            evidence_reasons=assessment.evidence_reasons,
            evidence_warnings=assessment.evidence_warnings,
            claim_verifications=claim_verification_service.verify(generated, selected_chunks),
            why_this_answer=self._why_this_answer(answer_source, assessment.evidence_strength, selected_chunks),
            insufficient_evidence=False,
            supporting_chunks=selected_chunks,
            warnings=retrieval.warnings,
        )
        observability_service.record_latency("ask", (time.perf_counter() - started) * 1000)
        return response

    def _build_prompt(self, question: str, chunks: list[SearchResult]) -> str:
        context = "\n\n".join(
            f"[chunk:{chunk.chunk_id}] {chunk.document_title} (chunk {chunk.chunk_index}, page {chunk.page_number or 'n/a'})\n{chunk.raw_text}"
            for chunk in chunks
        )
        return (
            "You are answering from a document retrieval system.\n"
            "Use only the provided context.\n"
            "Do not invent facts, dates, names, or explanations that are not directly supported.\n"
            "If the evidence is insufficient, reply that the information is not supported by the uploaded documents.\n"
            "When you make a supported claim, attach the relevant chunk citations in square brackets using the provided chunk ids.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}\n\n"
            "Answer concisely and keep every claim tied to evidence."
        )

    def _fallback_answer(self, question: str, chunks: list[SearchResult]) -> str:
        if not chunks:
            return "The information is not found in the uploaded documents."

        query_terms = preprocess_text(question)
        ranked_sentences: list[tuple[float, str, int]] = []
        for chunk in chunks:
            for sentence in sentence_split(chunk.raw_text):
                ranked_sentences.append(
                    (lexical_overlap_score(sentence, query_terms) + chunk.score, sentence, chunk.chunk_id)
                )

        ranked_sentences.sort(key=lambda item: item[0], reverse=True)
        best = ranked_sentences[:4]
        if not best:
            return "The information is not found in the uploaded documents."

        body = " ".join(sentence for _, sentence, _ in best).strip()
        if not body.endswith("."):
            body += "."

        cited_chunk_ids: list[int] = []
        for _, _, chunk_id in best:
            if chunk_id not in cited_chunk_ids:
                cited_chunk_ids.append(chunk_id)

        citations = " ".join(f"[chunk:{chunk_id}]" for chunk_id in cited_chunk_ids[:3])
        return f"{make_snippet(body, 420)} {citations}".strip()

    def _context_before(self, text: str, snippet: str) -> str | None:
        index = text.find(snippet.strip(". "))
        if index <= 0:
            return None
        return make_snippet(text[max(0, index - 500):index], 280)

    def _context_after(self, text: str, snippet: str) -> str | None:
        needle = snippet.strip(". ")
        index = text.find(needle)
        if index < 0:
            return None
        end = index + len(needle)
        return make_snippet(text[end:end + 500], 280)

    def _select_supporting_chunks(self, results: list[SearchResult], limit: int) -> list[SearchResult]:
        selected: list[SearchResult] = []
        seen_signatures: list[set[str]] = []
        per_document_counts: defaultdict[int, int] = defaultdict(int)

        for result in results:
            signature = set(preprocess_text(result.raw_text[:700]))
            if self._is_near_duplicate(signature, seen_signatures):
                continue
            if per_document_counts[result.document_id] >= 2 and len(selected) < min(limit, 4):
                continue

            selected.append(result)
            seen_signatures.append(signature)
            per_document_counts[result.document_id] += 1

            if len(selected) >= limit:
                break

        selected.sort(key=lambda item: (item.document_id, item.chunk_index, -item.score))
        return selected

    def _is_insufficient_evidence(self, results: list[SearchResult]) -> bool:
        if not results:
            return True
        top_score = max(result.score for result in results)
        total_supported_terms = len({term for result in results for term in result.matched_terms})
        return top_score < settings.ask_min_grounded_score or total_supported_terms < settings.ask_min_supported_terms

    def _is_near_duplicate(self, signature: set[str], seen_signatures: list[set[str]]) -> bool:
        if not signature:
            return False
        for previous in seen_signatures:
            intersection = len(signature & previous)
            union = len(signature | previous)
            if union and (intersection / union) >= 0.8:
                return True
        return False

    def _why_this_answer(self, answer_source: str, evidence_strength: EvidenceStrength, chunks: list[SearchResult]) -> WhyAnswerSummary:
        used_chunks = [
            WhyAnswerChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                score=round(chunk.score, 4),
                reason="; ".join(chunk.rerank_reasons) if chunk.rerank_reasons else chunk.explanation.summary,
            )
            for chunk in chunks
        ]
        source_label = "LLM synthesis" if answer_source == "llm" else "extractive fallback"
        if answer_source == "insufficient_evidence":
            source_label = "insufficient evidence guardrail"
        return WhyAnswerSummary(
            answer_source=answer_source,
            evidence_strength=evidence_strength,
            used_chunks=used_chunks,
            summary=(
                f"This answer used {len(used_chunks)} retrieved chunk(s), was generated via {source_label}, "
                f"and the evidence was assessed as {evidence_strength}."
            ),
        )


rag_service = RagService()
