import logging
from dataclasses import dataclass

from app.core.config import get_settings
from app.models.schemas import SearchResult
from app.utils.text import preprocess_text


logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class RerankDiagnostics:
    degraded: bool
    warning: str | None = None


class RerankingService:
    def __init__(self) -> None:
        self._model = None
        self._model_attempted = False
        self._diagnostics = RerankDiagnostics(degraded=True, warning="Using deterministic reranking fallback.")

    def rerank(self, query: str, results: list[SearchResult], limit: int) -> tuple[list[SearchResult], list[str]]:
        if not settings.reranking_enabled or not results:
            return results[:limit], []

        original_positions = {result.chunk_id: index + 1 for index, result in enumerate(results)}
        cross_scores = self._cross_encoder_scores(query, results)
        query_terms = preprocess_text(query)
        scored: list[tuple[float, SearchResult, list[str]]] = []

        for result in results:
            if cross_scores is not None:
                score = float(cross_scores.get(result.chunk_id, 0.0))
                reasons = ["Cross-encoder relevance score available."]
            else:
                score, reasons = self._deterministic_score(query, query_terms, result)
            result.original_rank = original_positions[result.chunk_id]
            result.rerank_score = round(score, 4)
            result.rerank_reasons = reasons
            scored.append((score, result, reasons))

        scored.sort(key=lambda item: (item[0], item[1].score), reverse=True)
        reranked = [item[1] for item in scored[:limit]]
        for index, result in enumerate(reranked, start=1):
            result.final_rank = index
        warnings = [self._diagnostics.warning] if self._diagnostics.warning else []
        return reranked, warnings

    def _cross_encoder_scores(self, query: str, results: list[SearchResult]) -> dict[int, float] | None:
        if self._model_attempted:
            model = self._model
        else:
            self._model_attempted = True
            model = None
            try:
                from sentence_transformers import CrossEncoder

                model = CrossEncoder(
                    settings.reranker_model,
                    automodel_args={"local_files_only": True},
                    tokenizer_args={"local_files_only": True},
                )
                self._diagnostics = RerankDiagnostics(degraded=False)
            except Exception as exc:
                logger.warning("Cross-encoder reranker unavailable; using deterministic fallback: %s", exc)
                self._diagnostics = RerankDiagnostics(
                    degraded=True,
                    warning=(
                        "Reranker model unavailable in the local model cache; deterministic reranking fallback is active."
                    ),
                )
            self._model = model

        if model is None:
            return None
        try:
            pairs = [(query, result.raw_text[:1200]) for result in results]
            scores = model.predict(pairs)
            return {result.chunk_id: float(score) for result, score in zip(results, scores)}
        except Exception as exc:
            logger.warning("Cross-encoder prediction failed; using deterministic fallback: %s", exc)
            self._diagnostics = RerankDiagnostics(
                degraded=True,
                warning="Reranker model failed at inference time; deterministic reranking fallback is active.",
            )
            return None

    def _deterministic_score(self, query: str, query_terms: list[str], result: SearchResult) -> tuple[float, list[str]]:
        text_terms = preprocess_text(result.raw_text)
        title_terms = preprocess_text(result.document_title)
        text_set = set(text_terms)
        title_set = set(title_terms)
        overlap = sorted(set(query_terms) & text_set)
        phrase_match = query.lower() in result.raw_text.lower()
        title_overlap = sorted(set(query_terms) & title_set)
        length_penalty = max(0.0, min(len(text_terms) / 1200, 0.2))
        keyword_component = len(overlap) / max(len(set(query_terms)), 1)
        title_component = 0.2 if title_overlap else 0.0
        phrase_component = 0.18 if phrase_match else 0.0
        semantic_component = min(float(result.semantic_score or 0), 1.0) * 0.25
        bm25_component = min(float(result.keyword_score or result.score or 0), 1.0) * 0.25
        score = keyword_component * 0.45 + phrase_component + title_component + semantic_component + bm25_component - length_penalty
        reasons: list[str] = []
        if overlap:
            reasons.append(f"keyword overlap: {', '.join(overlap[:5])}")
        if phrase_match:
            reasons.append("exact phrase match")
        if title_overlap:
            reasons.append("title match")
        if result.semantic_score is not None:
            reasons.append("semantic score carried forward")
        if result.keyword_score is not None:
            reasons.append("BM25 score carried forward")
        if length_penalty:
            reasons.append("long chunk length penalty applied")
        return max(score, 0.0), reasons or ["deterministic fallback score"]


reranking_service = RerankingService()
