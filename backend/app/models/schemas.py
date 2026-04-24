from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DocumentStatus = Literal["uploaded", "queued", "processing", "extracted", "chunked", "indexed", "failed"]
TaskStatus = Literal["queued", "processing", "chunked", "indexed", "failed"]
SearchMode = Literal["keyword", "semantic", "hybrid"]
WorkspaceRole = Literal["owner", "editor", "viewer"]
RetrievalPipelineName = Literal["bm25", "semantic", "hybrid", "hybrid_reranked"]
AnswerSource = Literal["llm", "extractive_fallback", "insufficient_evidence"]
EvidenceStrength = Literal["strong", "medium", "weak", "insufficient"]
ClaimStatus = Literal["supported", "partially_supported", "unsupported"]
ComparisonPointType = Literal["agreement", "difference", "unique"]


class ApiErrorResponse(BaseModel):
    detail: str


class UserPublic(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime


class SignupRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=8)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1)


class WorkspaceMember(BaseModel):
    user_id: int
    name: str
    email: str
    role: WorkspaceRole


class WorkspaceSummary(BaseModel):
    id: int
    name: str
    slug: str
    role: WorkspaceRole
    created_at: datetime


class WorkspaceDetail(WorkspaceSummary):
    members: list[WorkspaceMember] = Field(default_factory=list)


class WorkspaceMemberRequest(BaseModel):
    email: str = Field(min_length=1)
    role: WorkspaceRole = "viewer"


class WorkspaceMemberPatchRequest(BaseModel):
    role: WorkspaceRole


class DocumentSummary(BaseModel):
    id: int
    workspace_id: int | None = None
    title: str
    file_name: str
    file_type: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str | None = None
    keywords: list[str] = Field(default_factory=list)
    chunk_count: int
    uploaded_at: datetime
    last_indexed_at: datetime | None
    checksum: str
    status: DocumentStatus
    status_message: str | None = None
    page_count: int | None = None
    progress: int = Field(default=0, ge=0, le=100)
    task_id: str | None = None
    error_message: str | None = None
    indexed_at: datetime | None = None
    source_type: str = "upload"
    source_url: str | None = None


class ChunkRecord(BaseModel):
    id: int
    document_id: int
    workspace_id: int | None = None
    chunk_index: int
    text: str
    token_count: int
    page_number: int | None = None


class DocumentDetail(DocumentSummary):
    chunks: list[ChunkRecord]


class UploadResponse(BaseModel):
    message: str
    documents: list[DocumentSummary]
    duplicates_skipped: int = 0
    failures: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    indexing_mode: str = "synchronous"
    warnings: list[str] = Field(default_factory=list)


class TaskSummary(BaseModel):
    task_id: str
    document_id: int
    workspace_id: int | None = None
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    indexing_mode: str = "synchronous"


class DocumentFilter(BaseModel):
    document_id: int | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=25)
    document_id: int | None = None
    workspace_id: int | None = None


class SearchExplanation(BaseModel):
    keyword_overlap: list[str] = Field(default_factory=list)
    semantic_match: bool = False
    title_match: bool = False
    keyword_score: float | None = None
    semantic_score: float | None = None
    hybrid_score: float | None = None
    title_boost_applied: bool = False
    score_breakdown: list[str] = Field(default_factory=list)
    summary: str


class SearchResult(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    page_number: int | None = None
    score: float
    keyword_score: float | None = None
    semantic_score: float | None = None
    snippet: str
    highlighted_snippet: str
    raw_text: str
    matched_terms: list[str] = Field(default_factory=list)
    retrieval_mode: SearchMode
    explanation: SearchExplanation
    rerank_score: float | None = None
    rerank_reasons: list[str] = Field(default_factory=list)
    original_rank: int | None = None
    final_rank: int | None = None
    source_url: str | None = None


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResult]
    warnings: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    chunk_text_snippet: str
    supporting_chunk_text: str
    highlighted_snippet: str
    matched_terms: list[str] = Field(default_factory=list)
    explanation_summary: str
    page_number: int | None = None
    before_context: str | None = None
    after_context: str | None = None
    source_url: str | None = None


class WhyAnswerChunk(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    page_number: int | None = None
    score: float
    reason: str


class WhyAnswerSummary(BaseModel):
    answer_source: AnswerSource
    evidence_strength: EvidenceStrength
    used_chunks: list[WhyAnswerChunk] = Field(default_factory=list)
    summary: str


class ClaimVerification(BaseModel):
    claim: str
    status: ClaimStatus
    confidence: int = Field(ge=0, le=100)
    evidence_chunk_ids: list[int] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    reason: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=6, ge=1, le=12)
    document_id: int | None = None
    workspace_id: int | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieval_query: str
    grounded: bool
    answer_source: AnswerSource
    evidence_strength: EvidenceStrength
    evidence_score: int = Field(default=0, ge=0, le=100)
    evidence_reasons: list[str] = Field(default_factory=list)
    evidence_warnings: list[str] = Field(default_factory=list)
    claim_verifications: list[ClaimVerification] = Field(default_factory=list)
    why_this_answer: WhyAnswerSummary
    insufficient_evidence: bool = False
    supporting_chunks: list[SearchResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CompareRequest(BaseModel):
    document_ids: list[int] = Field(min_length=2, max_length=4)
    question: str | None = None
    workspace_id: int | None = None


class ComparisonPoint(BaseModel):
    text: str
    document_ids: list[int] = Field(default_factory=list)
    supporting_chunk_ids: list[int] = Field(default_factory=list)
    confidence: int = Field(ge=0, le=100)
    type: ComparisonPointType


class CompareResponse(BaseModel):
    comparison_summary: str
    agreements: list[ComparisonPoint] = Field(default_factory=list)
    differences: list[ComparisonPoint] = Field(default_factory=list)
    unique_points: list[ComparisonPoint] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    evidence_score: int = Field(ge=0, le=100)
    evidence_reasons: list[str] = Field(default_factory=list)
    evidence_warnings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StatsSummary(BaseModel):
    document_count: int
    indexed_document_count: int
    chunk_count: int
    last_indexed_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    database_ready: bool
    uploads_path: str
    index_path: str
    embedding_model: str
    embedding_model_ready: bool


class HealthDetailedResponse(HealthResponse):
    environment: str
    database_path: str
    temp_path: str
    cors_origins: list[str] = Field(default_factory=list)
    cors_origin_regex: str | None = None
    bm25_ready: bool
    faiss_index_present: bool
    semantic_search_ready: bool
    embedding_model_status: str
    llm_configured: bool


class EvaluationCase(BaseModel):
    question: str
    expected_terms: list[str] = Field(default_factory=list)
    expected_document_titles: list[str] = Field(default_factory=list)
    expected_citation_chunk_ids: list[int] = Field(default_factory=list)
    ideal_answer_summary: str | None = None


class EvaluationQuestionResult(BaseModel):
    question: str
    top_k_recall: float
    citation_match_rate: float
    unsupported_claim_rate: float
    average_evidence_score: float
    groundedness_score: float
    answer_latency_ms: float
    search_latency_ms: float
    matched_terms: list[str] = Field(default_factory=list)
    matched_document_titles: list[str] = Field(default_factory=list)
    expected_document_titles: list[str] = Field(default_factory=list)
    expected_citation_chunk_ids: list[int] = Field(default_factory=list)
    returned_citation_chunk_ids: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    dataset_size: int
    corpus_document_count: int
    top_k_recall: float
    citation_match_rate: float
    unsupported_claim_rate: float
    average_evidence_score: float
    groundedness_score: float
    average_answer_latency_ms: float
    average_search_latency_ms: float
    warnings: list[str] = Field(default_factory=list)
    ran_at: datetime | None = None


class EvaluationRunResponse(BaseModel):
    summary: EvaluationSummary
    results: list[EvaluationQuestionResult] = Field(default_factory=list)


class SystemMetrics(BaseModel):
    search_latency_ms: float
    ask_latency_ms: float
    indexing_latency_ms: float
    failed_indexing_count: int
    total_documents_indexed: int
    total_chunks_indexed: int
    warnings: list[str] = Field(default_factory=list)


class EvalSetCreateRequest(BaseModel):
    workspace_id: int | None = None
    name: str = Field(min_length=1)
    description: str | None = None


class EvalQuestionCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    expected_answer: str | None = None
    expected_terms: list[str] = Field(default_factory=list)
    expected_document_ids: list[int] = Field(default_factory=list)
    expected_citation_chunk_ids: list[int] = Field(default_factory=list)


class EvalQuestionPatchRequest(BaseModel):
    question: str | None = None
    expected_answer: str | None = None
    expected_terms: list[str] | None = None
    expected_document_ids: list[int] | None = None
    expected_citation_chunk_ids: list[int] | None = None


class EvalQuestionPublic(BaseModel):
    id: int
    eval_set_id: int
    workspace_id: int
    question: str
    expected_answer: str | None = None
    expected_terms: list[str] = Field(default_factory=list)
    expected_document_ids: list[int] = Field(default_factory=list)
    expected_citation_chunk_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class EvalSetPublic(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: str | None = None
    created_at: datetime
    questions: list[EvalQuestionPublic] = Field(default_factory=list)


class EvalRunPublic(BaseModel):
    id: int
    eval_set_id: int
    workspace_id: int
    summary: EvaluationSummary
    results: list[EvaluationQuestionResult] = Field(default_factory=list)
    created_at: datetime


class RetrievalPlaygroundRequest(BaseModel):
    workspace_id: int | None = None
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=15)
    pipelines: list[RetrievalPipelineName] = Field(default_factory=lambda: ["bm25", "semantic", "hybrid_reranked"])


class RetrievalPipelineResult(BaseModel):
    pipeline: RetrievalPipelineName
    results: list[SearchResult] = Field(default_factory=list)
    latency_ms: float
    warnings: list[str] = Field(default_factory=list)


class RetrievalPlaygroundResponse(BaseModel):
    query: str
    pipelines: list[RetrievalPipelineResult] = Field(default_factory=list)


class IndexLogEntry(BaseModel):
    id: int
    workspace_id: int
    document_id: int | None = None
    level: str
    message: str
    created_at: datetime


class IndexStatusResponse(BaseModel):
    workspace_id: int
    document_count: int
    indexed_document_count: int
    chunk_count: int
    failed_tasks: int
    queue_mode: str
    redis_available: bool
    warnings: list[str] = Field(default_factory=list)


class WebUrlImportRequest(BaseModel):
    workspace_id: int | None = None
    url: str = Field(min_length=1)


class ConnectorImportResponse(BaseModel):
    document: DocumentSummary
    task_id: str | None = None
    indexing_mode: str
    warnings: list[str] = Field(default_factory=list)


class AdminObservabilityResponse(SystemMetrics):
    queue_mode: str
    redis_available: bool
    document_count: int
    chunk_count: int
    evaluation_runs: int
    task_failure_count: int


class ApiKeyCreateRequest(BaseModel):
    workspace_id: int | None = None
    name: str = Field(min_length=1)


class ApiKeyPublic(BaseModel):
    id: int
    workspace_id: int
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    api_key: str | None = None


class ApiRetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class ApiRerankRequest(BaseModel):
    query: str = Field(min_length=1)
    results: list[SearchResult]


class ApiAnswerRequest(BaseModel):
    question: str = Field(min_length=1)
    limit: int = Field(default=6, ge=1, le=12)


class ApiEvaluateRequest(BaseModel):
    eval_set_id: int | None = None
