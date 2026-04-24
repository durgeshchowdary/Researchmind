from app.services.chunking_service import chunking_service, settings as chunk_settings
from app.services.rag_service import rag_service
from app.services.ranking_service import ranking_service
from app.services.reranking_service import reranking_service
from app.services.task_service import task_service
from app.models.schemas import SearchExplanation, SearchResult
from app.utils.text import lexical_overlap_score, preprocess_text, sentence_split


def test_preprocess_text_removes_stopwords_and_normalizes_tokens() -> None:
    tokens = preprocess_text("This is a Hybrid retrieval system for the documents, and it works.")
    assert "hybrid" in tokens
    assert "retrieval" in tokens
    assert "documents" in tokens
    assert "this" not in tokens
    assert "and" not in tokens


def test_chunking_preserves_page_numbers_and_overlap() -> None:
    original_chunk_size = chunk_settings.chunk_size
    original_chunk_overlap = chunk_settings.chunk_overlap
    chunk_settings.chunk_size = 6
    chunk_settings.chunk_overlap = 2
    try:
        chunks = chunking_service.chunk_text(
            "",
            sections=[
                {"page_number": 1, "text": "alpha beta gamma delta epsilon zeta eta theta"},
                {"page_number": 2, "text": "iota kappa lambda mu"},
            ],
        )
    finally:
        chunk_settings.chunk_size = original_chunk_size
        chunk_settings.chunk_overlap = original_chunk_overlap

    assert len(chunks) >= 2
    assert chunks[0]["page_number"] == 1
    assert any(chunk["page_number"] == 2 for chunk in chunks)


def test_bm25_prefers_documents_with_query_term_density() -> None:
    scores = ranking_service.bm25_score(
        ["hybrid", "search"],
        {
            "hybrid": {1: 3, 2: 1},
            "search": {1: 2, 2: 1},
        },
        {"hybrid": 2, "search": 2},
        {1: 20, 2: 40},
        avg_chunk_length=30,
        limit=5,
        title_matches={1: 2.0, 2: 0.0},
        title_boost=0.25,
    )

    assert scores[0][0] == 1
    assert scores[0][1] > scores[1][1]


def test_hybrid_fusion_combines_normalized_scores() -> None:
    fused = ranking_service.fuse_scores(
        [(10, 8.0), (11, 4.0)],
        [(11, 0.9), (12, 0.8)],
        bm25_weight=0.6,
        semantic_weight=0.4,
        limit=5,
    )

    assert fused[0][0] in {10, 11}
    assert {item[0] for item in fused} == {10, 11, 12}


def test_extractive_helpers_score_and_split_sentences() -> None:
    sentences = sentence_split("Hybrid search improves recall. Grounded answers need evidence!")
    score = lexical_overlap_score("Hybrid search improves recall.", ["hybrid", "recall"])

    assert len(sentences) == 2
    assert score > 0


def test_fallback_answer_includes_chunk_citations() -> None:
    answer = rag_service._fallback_answer(
        "Why is hybrid retrieval useful?",
        [
            SearchResult(
                chunk_id=101,
                document_id=1,
                document_title="Doc A",
                chunk_index=0,
                page_number=1,
                score=0.8,
                keyword_score=0.7,
                semantic_score=0.6,
                snippet="Hybrid retrieval improves recall.",
                highlighted_snippet="Hybrid retrieval improves recall.",
                raw_text="Hybrid retrieval improves recall and keeps answers grounded in evidence.",
                matched_terms=["hybrid", "retrieval"],
                retrieval_mode="hybrid",
                explanation=SearchExplanation(summary="good match"),
            )
        ],
    )

    assert "[chunk:101]" in answer


def test_supporting_chunk_selection_deduplicates_near_identical_results() -> None:
    results = [
        SearchResult(
            chunk_id=1,
            document_id=11,
            document_title="Doc One",
            chunk_index=0,
            page_number=1,
            score=0.9,
            keyword_score=0.8,
            semantic_score=0.9,
            snippet="Alpha beta gamma",
            highlighted_snippet="Alpha beta gamma",
            raw_text="Alpha beta gamma delta epsilon zeta eta theta",
            matched_terms=["alpha"],
            retrieval_mode="hybrid",
            explanation=SearchExplanation(summary="top result"),
        ),
        SearchResult(
            chunk_id=2,
            document_id=11,
            document_title="Doc One",
            chunk_index=1,
            page_number=1,
            score=0.85,
            keyword_score=0.75,
            semantic_score=0.88,
            snippet="Alpha beta gamma",
            highlighted_snippet="Alpha beta gamma",
            raw_text="Alpha beta gamma delta epsilon zeta eta theta",
            matched_terms=["alpha"],
            retrieval_mode="hybrid",
            explanation=SearchExplanation(summary="duplicate"),
        ),
    ]

    selected = rag_service._select_supporting_chunks(results, limit=4)

    assert len(selected) == 1


def test_deterministic_reranker_orders_better_lexical_match_higher() -> None:
    reranking_service._model_attempted = True
    reranking_service._model = None
    results = [
        SearchResult(
            chunk_id=1,
            document_id=11,
            document_title="General Notes",
            chunk_index=0,
            score=0.3,
            snippet="unrelated",
            highlighted_snippet="unrelated",
            raw_text="This chunk discusses unrelated governance details.",
            matched_terms=[],
            retrieval_mode="hybrid",
            explanation=SearchExplanation(summary="weak"),
        ),
        SearchResult(
            chunk_id=2,
            document_id=12,
            document_title="Hybrid Retrieval",
            chunk_index=0,
            score=0.2,
            snippet="hybrid retrieval",
            highlighted_snippet="hybrid retrieval",
            raw_text="Hybrid retrieval combines BM25 keyword search with semantic vector search.",
            matched_terms=["hybrid", "retrieval"],
            retrieval_mode="hybrid",
            explanation=SearchExplanation(summary="strong"),
        ),
    ]

    reranked, warnings = reranking_service.rerank("hybrid retrieval semantic search", results, 2)

    assert reranked[0].chunk_id == 2
    assert reranked[0].rerank_score is not None
    assert reranked[0].original_rank == 2
    assert reranked[0].final_rank == 1
    assert reranked[0].rerank_reasons
    assert isinstance(warnings, list)


def test_task_service_falls_back_when_redis_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(task_service, "redis_available", lambda: False)

    assert task_service.indexing_mode() == "background"
