import time

from app.core.config import get_settings
from app.models.schemas import SearchExplanation, SearchRequest, SearchResponse, SearchResult
from app.services.document_service import document_service
from app.services.indexing_service import indexing_service
from app.services.observability_service import observability_service
from app.services.ranking_service import ranking_service
from app.services.reranking_service import reranking_service
from app.services.workspace_service import workspace_service
from app.utils.text import highlight_terms, make_snippet, preprocess_text


settings = get_settings()


class SearchService:
    def keyword_search(self, payload: SearchRequest, user_id: int | None = None) -> SearchResponse:
        query_terms = preprocess_text(payload.query)
        scored = indexing_service.bm25_score(query_terms, payload.limit)
        return self._build_response(
            payload.query,
            scored,
            query_terms,
            "keyword",
            payload.document_id,
            user_id,
            workspace_id=payload.workspace_id,
            warnings=self._warnings_for_mode("keyword"),
        )

    def semantic_search(self, payload: SearchRequest, user_id: int | None = None) -> SearchResponse:
        scored = indexing_service.semantic_score(payload.query, payload.limit)
        return self._build_response(
            payload.query,
            scored,
            preprocess_text(payload.query),
            "semantic",
            payload.document_id,
            user_id,
            workspace_id=payload.workspace_id,
            warnings=self._warnings_for_mode("semantic"),
        )

    def hybrid_search(self, payload: SearchRequest, user_id: int | None = None) -> SearchResponse:
        started = time.perf_counter()
        query_terms = preprocess_text(payload.query)
        retrieval_limit = max(20, payload.limit * 4)
        bm25 = indexing_service.bm25_score(query_terms, retrieval_limit)
        semantic = indexing_service.semantic_score(payload.query, retrieval_limit)
        warnings = self._warnings_for_mode("hybrid")

        if bm25 and not semantic:
            response = self._build_response(
                payload.query,
                bm25,
                query_terms,
                "hybrid",
                payload.document_id,
                user_id,
                workspace_id=payload.workspace_id,
                component_scores={
                    chunk_id: {
                        "keyword_score": keyword_score,
                        "semantic_score": None,
                    }
                    for chunk_id, keyword_score in bm25
                },
                warnings=warnings + ["Hybrid ranking fell back to keyword-only mode because semantic retrieval is unavailable."],
                final_limit=payload.limit,
            )
            observability_service.record_latency("search", (time.perf_counter() - started) * 1000)
            return response

        combined = ranking_service.fuse_scores(
            bm25,
            semantic,
            bm25_weight=settings.hybrid_bm25_weight,
            semantic_weight=settings.hybrid_semantic_weight,
            limit=retrieval_limit,
        )
        response = self._build_response(
            payload.query,
            [(chunk_id, score) for chunk_id, score, _, _ in combined],
            query_terms,
            "hybrid",
            payload.document_id,
            user_id,
            workspace_id=payload.workspace_id,
            component_scores={
                chunk_id: {
                    "keyword_score": keyword_score,
                    "semantic_score": semantic_score,
                }
                for chunk_id, _, keyword_score, semantic_score in combined
            },
            warnings=warnings,
            final_limit=payload.limit,
        )
        observability_service.record_latency("search", (time.perf_counter() - started) * 1000)
        return response

    def _build_response(
        self,
        query: str,
        scored: list[tuple[int, float]],
        query_terms: list[str],
        retrieval_mode: str,
        document_id: int | None = None,
        user_id: int | None = None,
        component_scores: dict[int, dict[str, float | None]] | None = None,
        warnings: list[str] | None = None,
        final_limit: int | None = None,
        workspace_id: int | None = None,
    ) -> SearchResponse:
        workspace_id = workspace_service.resolve_workspace_id(user_id, workspace_id) if user_id is not None else workspace_id
        chunk_map = document_service.get_chunk_rows(
            [chunk_id for chunk_id, _ in scored],
            document_id=document_id,
            user_id=user_id,
            workspace_id=workspace_id,
        )
        results: list[SearchResult] = []
        for chunk_id, score in scored:
            row = chunk_map.get(chunk_id)
            if not row:
                continue
            if document_id is not None and row["document_id"] != document_id:
                continue
            snippet = self._build_snippet(row["text"], query_terms)
            highlighted = highlight_terms(snippet, query_terms) if query_terms else snippet
            keyword_overlap = sorted(set(query_terms) & set(preprocess_text(row["text"])))
            title_terms = set(preprocess_text(row["document_title"]))
            title_match = bool(set(query_terms) & title_terms)
            score_parts = component_scores.get(chunk_id, {}) if component_scores else {}
            score_breakdown = self._score_breakdown(score_parts, keyword_overlap, title_match, retrieval_mode, score)
            semantic_match = self._semantic_match(score_parts, retrieval_mode)
            results.append(
                SearchResult(
                    chunk_id=row["chunk_id"],
                    document_id=row["document_id"],
                    document_title=row["document_title"],
                    chunk_index=row["chunk_index"],
                    page_number=row["page_number"],
                    score=round(float(score), 4),
                    keyword_score=score_parts.get("keyword_score"),
                    semantic_score=score_parts.get("semantic_score"),
                    snippet=snippet,
                    highlighted_snippet=highlighted,
                    raw_text=row["text"],
                    matched_terms=keyword_overlap,
                    retrieval_mode=retrieval_mode,
                    source_url=row.get("source_url"),
                    explanation=SearchExplanation(
                        keyword_overlap=keyword_overlap,
                        semantic_match=semantic_match,
                        title_match=title_match,
                        keyword_score=score_parts.get("keyword_score"),
                        semantic_score=score_parts.get("semantic_score"),
                        hybrid_score=round(float(score), 4),
                        title_boost_applied=title_match,
                        score_breakdown=score_breakdown,
                        summary=self._explain_result(keyword_overlap, title_match, semantic_match),
                    ),
                )
            )
        if retrieval_mode == "hybrid" and final_limit is not None:
            results, rerank_warnings = reranking_service.rerank(query, results, final_limit)
            warnings = (warnings or []) + rerank_warnings
            movement_by_id = {
                result.chunk_id: (result.original_rank or 0) - (result.final_rank or 0)
                for result in results
                if result.original_rank and result.final_rank
            }
            for result in results:
                movement = movement_by_id.get(result.chunk_id, 0)
                if movement > 0:
                    result.explanation.score_breakdown.append(f"Moved up {movement} position(s) after reranking")
                elif movement < 0:
                    result.explanation.score_breakdown.append(f"Moved down {abs(movement)} position(s) after reranking")
        elif final_limit is not None:
            results = results[:final_limit]
        return SearchResponse(query=query, total=len(results), results=results, warnings=warnings or [])

    def _build_snippet(self, text: str, query_terms: list[str]) -> str:
        normalized_text = " ".join(text.split())
        if not query_terms:
            return make_snippet(normalized_text)
        lowered = normalized_text.lower()
        best_index = min(
            (lowered.find(term.lower()) for term in query_terms if lowered.find(term.lower()) >= 0),
            default=-1,
        )
        if best_index < 0:
            return make_snippet(normalized_text)
        start = max(best_index - 80, 0)
        end = min(best_index + 180, len(normalized_text))
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(normalized_text) else ""
        return f"{prefix}{normalized_text[start:end].strip()}{suffix}"

    def _semantic_match(self, score_parts: dict[str, float | None], retrieval_mode: str) -> bool:
        if retrieval_mode == "semantic":
            return True
        if retrieval_mode == "hybrid":
            return (score_parts.get("semantic_score") or 0) > 0
        return False

    def _explain_result(self, keyword_overlap: list[str], title_match: bool, semantic_match: bool) -> str:
        reasons: list[str] = []
        if keyword_overlap:
            reasons.append(f"matched keywords: {', '.join(keyword_overlap[:4])}")
        if semantic_match:
            reasons.append("high semantic similarity")
        if title_match:
            reasons.append("query terms also matched the document title")
        return "; ".join(reasons) if reasons else "retrieved from the ranked evidence set"

    def _score_breakdown(
        self,
        score_parts: dict[str, float | None],
        keyword_overlap: list[str],
        title_match: bool,
        retrieval_mode: str,
        score: float,
    ) -> list[str]:
        details: list[str] = []
        if keyword_overlap:
            details.append(f"Keyword overlap: {', '.join(keyword_overlap[:5])}")
        if score_parts.get("keyword_score") is not None:
            if retrieval_mode == "hybrid" and score_parts.get("semantic_score") is None:
                details.append(f"Keyword-only fallback score: {float(score_parts['keyword_score'] or 0):.4f}")
            elif retrieval_mode == "hybrid":
                details.append(f"Normalized BM25 contribution: {float(score_parts['keyword_score'] or 0):.3f}")
            else:
                details.append(f"Keyword score: {float(score_parts['keyword_score'] or 0):.4f}")
        if score_parts.get("semantic_score") is not None:
            details.append(f"Normalized semantic contribution: {float(score_parts['semantic_score'] or 0):.3f}")
        if title_match:
            details.append("Document title matched the query")
        details.append(f"{retrieval_mode.capitalize()} score: {float(score):.4f}")
        return details

    def _warnings_for_mode(self, mode: str) -> list[str]:
        warnings: list[str] = []
        status = indexing_service.status_summary()
        if mode in {"semantic", "hybrid"} and not bool(status["vector_ready"]):
            warnings.append(
                "Semantic retrieval is currently unavailable because the FAISS index or embedding model is not ready."
            )
        return warnings


search_service = SearchService()
