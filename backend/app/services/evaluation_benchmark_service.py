import json
import time
from datetime import datetime, timezone

from pydantic import ValidationError

from app.core.config import get_settings
from app.models.schemas import (
    AskRequest,
    EvaluationCase,
    EvaluationQuestionResult,
    EvaluationRunResponse,
    EvaluationSummary,
    SearchRequest,
)
from app.services.document_service import document_service
from app.services.rag_service import rag_service
from app.services.search_service import search_service


settings = get_settings()


class EvaluationBenchmarkService:
    def __init__(self) -> None:
        self._latest: EvaluationRunResponse | None = None

    async def run(self, user_id: int | None = None) -> EvaluationRunResponse:
        dataset, dataset_warnings = self._load_dataset()
        response = await self.run_cases(dataset, user_id, None, dataset_warnings)
        self._latest = response
        return response

    async def run_cases(
        self,
        dataset: list[EvaluationCase],
        user_id: int | None = None,
        workspace_id: int | None = None,
        dataset_warnings: list[str] | None = None,
    ) -> EvaluationRunResponse:
        stats = document_service.get_stats(user_id, workspace_id)
        warnings = list(dataset_warnings or [])
        if not dataset:
            warnings.append("Evaluation dataset is missing or empty.")
        if stats.document_count == 0:
            warnings.append("Corpus is empty; upload documents before running evaluation.")
        if dataset and not any(item.expected_citation_chunk_ids for item in dataset):
            warnings.append("Evaluation dataset has no expected citation chunk ids; citation match rate is reported as 0.")

        results: list[EvaluationQuestionResult] = []
        for item in dataset:
            search_started = time.perf_counter()
            search = search_service.hybrid_search(SearchRequest(query=item.question, limit=8, workspace_id=workspace_id), user_id)
            search_latency_ms = (time.perf_counter() - search_started) * 1000

            ask_started = time.perf_counter()
            answer = await rag_service.answer_question(AskRequest(question=item.question, limit=6, workspace_id=workspace_id), user_id)
            answer_latency_ms = (time.perf_counter() - ask_started) * 1000

            matched_terms = sorted({term for result in search.results for term in result.matched_terms})
            matched_titles = sorted({result.document_title for result in search.results})
            top_k_recall = self._term_recall(item.expected_terms, matched_terms)
            if item.expected_document_titles:
                title_recall = self._title_recall(item.expected_document_titles, matched_titles)
                top_k_recall = (top_k_recall + title_recall) / 2 if item.expected_terms else title_recall

            returned_citations = [citation.chunk_id for citation in answer.citations]
            citation_match_rate = self._citation_match_rate(item.expected_citation_chunk_ids, returned_citations)
            question_warnings: list[str] = []
            if not item.expected_citation_chunk_ids:
                question_warnings.append("No expected citation chunk ids were provided for this question.")
            if not item.expected_terms and not item.expected_document_titles:
                question_warnings.append("No expected terms or document titles were provided for top-k recall.")
            unsupported = [claim for claim in answer.claim_verifications if claim.status == "unsupported"]
            unsupported_claim_rate = len(unsupported) / len(answer.claim_verifications) if answer.claim_verifications else 0.0
            groundedness = max(0.0, min(1.0, (answer.evidence_score / 100) * (1 - unsupported_claim_rate)))

            results.append(
                EvaluationQuestionResult(
                    question=item.question,
                    top_k_recall=round(top_k_recall, 4),
                    citation_match_rate=round(citation_match_rate, 4),
                    unsupported_claim_rate=round(unsupported_claim_rate, 4),
                    average_evidence_score=float(answer.evidence_score),
                    groundedness_score=round(groundedness, 4),
                    answer_latency_ms=round(answer_latency_ms, 2),
                    search_latency_ms=round(search_latency_ms, 2),
                    matched_terms=matched_terms,
                    matched_document_titles=matched_titles,
                    expected_document_titles=item.expected_document_titles,
                    expected_citation_chunk_ids=item.expected_citation_chunk_ids,
                    returned_citation_chunk_ids=returned_citations,
                    warnings=question_warnings + search.warnings + answer.warnings,
                )
            )

        summary = self._summary(results, stats.document_count, len(dataset), warnings)
        return EvaluationRunResponse(summary=summary, results=results)

    def latest_summary(self) -> EvaluationSummary:
        if self._latest:
            return self._latest.summary
        dataset, warnings = self._load_dataset()
        if not dataset:
            warnings.append("Run /evaluation/run after adding an evaluation dataset.")
        return EvaluationSummary(
            dataset_size=len(dataset),
            corpus_document_count=document_service.get_stats(None).document_count,
            top_k_recall=0,
            citation_match_rate=0,
            unsupported_claim_rate=0,
            average_evidence_score=0,
            groundedness_score=0,
            average_answer_latency_ms=0,
            average_search_latency_ms=0,
            warnings=warnings or ["No cached evaluation summary is available yet."],
            ran_at=None,
        )

    def _load_dataset(self) -> tuple[list[EvaluationCase], list[str]]:
        path = settings.evaluation_dataset_file
        if not path.exists():
            return [], [f"Evaluation dataset not found at {path}."]
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return [], ["Evaluation dataset must be a JSON array."]
            return [EvaluationCase.model_validate(item) for item in raw], []
        except (json.JSONDecodeError, ValidationError) as exc:
            return [], [f"Evaluation dataset could not be parsed: {exc}"]

    def _summary(
        self,
        results: list[EvaluationQuestionResult],
        corpus_document_count: int,
        dataset_size: int,
        warnings: list[str],
    ) -> EvaluationSummary:
        return EvaluationSummary(
            dataset_size=dataset_size,
            corpus_document_count=corpus_document_count,
            top_k_recall=self._avg([item.top_k_recall for item in results]),
            citation_match_rate=self._avg([item.citation_match_rate for item in results]),
            unsupported_claim_rate=self._avg([item.unsupported_claim_rate for item in results]),
            average_evidence_score=self._avg([item.average_evidence_score for item in results]),
            groundedness_score=self._avg([item.groundedness_score for item in results]),
            average_answer_latency_ms=self._avg([item.answer_latency_ms for item in results]),
            average_search_latency_ms=self._avg([item.search_latency_ms for item in results]),
            warnings=warnings,
            ran_at=datetime.now(timezone.utc),
        )

    def _avg(self, values: list[float]) -> float:
        return round(sum(values) / len(values), 4) if values else 0.0

    def _term_recall(self, expected: list[str], actual: list[str]) -> float:
        if not expected:
            return 0.0
        actual_text = " ".join(actual).lower()
        return sum(1 for term in expected if term.lower() in actual_text) / len(expected)

    def _title_recall(self, expected: list[str], actual: list[str]) -> float:
        if not expected:
            return 0.0
        actual_text = " ".join(actual).lower()
        return sum(1 for title in expected if title.lower() in actual_text) / len(expected)

    def _citation_match_rate(self, expected: list[int], actual: list[int]) -> float:
        if not expected:
            return 0.0
        return len(set(expected) & set(actual)) / len(set(expected))


evaluation_benchmark_service = EvaluationBenchmarkService()
