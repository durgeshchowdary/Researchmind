import asyncio
from datetime import datetime, timezone

import pytest

from app.models.schemas import (
    AskRequest,
    Citation,
    CompareRequest,
    DocumentDetail,
    DocumentSummary,
    SearchExplanation,
    SearchResponse,
    SearchResult,
)
from app.services.claim_verification_service import claim_verification_service
from app.services.comparison_service import comparison_service
from app.services.evidence_service import evidence_service
from app.services.rag_service import rag_service


def result(
    chunk_id: int,
    document_id: int,
    text: str,
    score: float = 0.9,
    matched_terms: list[str] | None = None,
) -> SearchResult:
    terms = matched_terms or ["aspirin", "fever", "trial"]
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        document_title=f"Document {document_id}",
        chunk_index=chunk_id - 1,
        page_number=1,
        score=score,
        keyword_score=score,
        semantic_score=None,
        snippet=text[:180],
        highlighted_snippet=text[:180],
        raw_text=text,
        matched_terms=terms,
        retrieval_mode="keyword",
        explanation=SearchExplanation(
            keyword_overlap=terms,
            semantic_match=False,
            title_match=False,
            keyword_score=score,
            semantic_score=None,
            hybrid_score=score,
            title_boost_applied=False,
            score_breakdown=[f"Keyword score: {score}"],
            summary="matched retrieved evidence",
        ),
    )


def citation(search_result: SearchResult) -> Citation:
    return Citation(
        chunk_id=search_result.chunk_id,
        document_id=search_result.document_id,
        document_title=search_result.document_title,
        chunk_index=search_result.chunk_index,
        chunk_text_snippet=search_result.snippet,
        supporting_chunk_text=search_result.raw_text,
        highlighted_snippet=search_result.highlighted_snippet,
        matched_terms=search_result.matched_terms,
        explanation_summary=search_result.explanation.summary,
        page_number=search_result.page_number,
    )


def document(document_id: int, title: str, text: str) -> DocumentDetail:
    summary = DocumentSummary(
        id=document_id,
        title=title,
        file_name=f"{title}.txt",
        file_type="txt",
        chunk_count=1,
        uploaded_at=datetime.now(timezone.utc),
        last_indexed_at=datetime.now(timezone.utc),
        checksum=f"checksum-{document_id}",
        status="indexed",
        status_message="Indexed",
    )
    return DocumentDetail(
        **summary.model_dump(),
        chunks=[
            {
                "id": document_id * 10,
                "document_id": document_id,
                "chunk_index": 0,
                "text": text,
                "token_count": len(text.split()),
                "page_number": 1,
            }
        ],
    )


def test_evidence_strength_no_citations_is_insufficient() -> None:
    assessment = evidence_service.assess("What reduces fever?", [], [], "extractive_fallback")

    assert assessment.evidence_strength == "insufficient"
    assert assessment.evidence_score == 0
    assert assessment.evidence_warnings


def test_evidence_strength_multiple_supporting_chunks_is_strong_or_medium() -> None:
    first = result(1, 1, "Aspirin reduces fever in adults in a randomized trial.", 0.96)
    second = result(2, 2, "Aspirin fever reduction was also observed in a second trial.", 0.88)
    assessment = evidence_service.assess(
        "Does aspirin reduce fever in trials?",
        [citation(first), citation(second)],
        [first, second],
        "extractive_fallback",
        "Aspirin reduces fever in trials. [chunk:1] [chunk:2]",
    )

    assert assessment.evidence_strength in {"strong", "medium"}
    assert assessment.evidence_score >= 52


def test_claim_verification_supported_partial_and_unsupported() -> None:
    chunk = result(1, 1, "Aspirin reduces fever in adults according to a clinical trial.", 0.8)
    verifications = claim_verification_service.verify(
        "Aspirin reduces fever in adults. Aspirin prevents stroke in high risk adults. Quantum sensors improve yield.",
        [chunk],
    )

    assert verifications[0].status == "supported"
    assert verifications[1].status == "partially_supported"
    assert verifications[2].status == "unsupported"


def test_document_comparison_validates_document_count() -> None:
    with pytest.raises(ValueError):
        comparison_service.compare(CompareRequest(document_ids=[1], question=None), user_id=1)


def test_document_comparison_returns_points_and_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    docs = {
        1: document(1, "Fever Trial", "Aspirin fever trial adults dosage reduction safety adverse events."),
        2: document(2, "Clinical Review", "Aspirin fever clinical review adults efficacy safety contraindications."),
    }

    monkeypatch.setattr(
        "app.services.comparison_service.document_service.get_document_detail",
        lambda document_id, user_id=None: docs.get(document_id),
    )

    response = comparison_service.compare(CompareRequest(document_ids=[1, 2], question=None), user_id=1)

    assert response.citations
    assert response.agreements or response.unique_points or response.differences
    assert response.evidence_strength in {"strong", "medium", "weak", "insufficient"}


def test_ask_response_schema_includes_evidence_and_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    chunk = result(1, 1, "Aspirin reduces fever in adults according to a clinical trial.", 0.9)
    monkeypatch.setattr(
        "app.services.rag_service.search_service.hybrid_search",
        lambda payload, user_id=None: SearchResponse(query=payload.query, total=1, results=[chunk], warnings=[]),
    )

    async def generate(_: str) -> str:
        return "Aspirin reduces fever in adults. [chunk:1]"

    monkeypatch.setattr("app.services.rag_service.llm_client.generate", generate)

    response = asyncio.run(rag_service.answer_question(AskRequest(question="Does aspirin reduce fever?", limit=3), user_id=1))

    assert response.evidence_score >= 0
    assert response.evidence_reasons
    assert response.claim_verifications
    assert response.claim_verifications[0].status == "supported"
