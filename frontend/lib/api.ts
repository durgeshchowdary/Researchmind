import {
  ApiErrorResponse,
  AdminObservabilityResponse,
  AnswerSource,
  ApiKeyPublic,
  AskResponse,
  Citation,
  ClaimStatus,
  CompareResponse,
  ComparisonPointType,
  DocumentStatus,
  DocumentSummary,
  EvidenceStrength,
  EvalRunPublic,
  EvalSetPublic,
  EvaluationRunResponse,
  EvaluationSummary,
  HealthDetailedResponse,
  HealthResponse,
  SearchMode,
  SearchResponse,
  StatsSummary,
  SystemMetrics,
  ConnectorImportResponse,
  IndexLogEntry,
  IndexStatusResponse,
  RetrievalPipelineName,
  RetrievalPlaygroundResponse,
  TaskStatus,
  TaskSummary,
  UploadResponse,
  WorkspaceDetail,
  WorkspaceRole,
  WorkspaceSummary,
} from "@/types/api";
import { getAuthToken, logout } from "@/lib/auth";

const configuredBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
const API_BASE_URL = configuredBaseUrl || "";
const REQUEST_TIMEOUT_MS = 30000;

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNullableString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function asDocumentStatus(value: unknown): DocumentStatus {
  return value === "uploaded" ||
    value === "queued" ||
    value === "processing" ||
    value === "extracted" ||
    value === "chunked" ||
    value === "indexed" ||
    value === "failed"
    ? value
    : "failed";
}

function asTaskStatus(value: unknown): TaskStatus {
  return value === "queued" || value === "processing" || value === "chunked" || value === "indexed" || value === "failed"
    ? value
    : "failed";
}

function asWorkspaceRole(value: unknown): WorkspaceRole {
  return value === "owner" || value === "editor" || value === "viewer" ? value : "viewer";
}

function asRetrievalPipelineName(value: unknown): RetrievalPipelineName {
  return value === "bm25" || value === "semantic" || value === "hybrid" || value === "hybrid_reranked"
    ? value
    : "hybrid";
}

function asSearchMode(value: unknown): SearchMode {
  return value === "keyword" || value === "semantic" || value === "hybrid" ? value : "hybrid";
}

function asAnswerSource(value: unknown): AnswerSource {
  return value === "llm" || value === "extractive_fallback" || value === "insufficient_evidence"
    ? value
    : "extractive_fallback";
}

function asEvidenceStrength(value: unknown): EvidenceStrength {
  return value === "strong" || value === "medium" || value === "weak" || value === "insufficient"
    ? value
    : "weak";
}

function asClaimStatus(value: unknown): ClaimStatus {
  return value === "supported" || value === "partially_supported" || value === "unsupported"
    ? value
    : "unsupported";
}

function asComparisonPointType(value: unknown): ComparisonPointType {
  return value === "agreement" || value === "difference" || value === "unique" ? value : "unique";
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const payload = (await response.json()) as ApiErrorResponse;
    const message = response.status === 401
      ? payload.detail || "Your session expired. Please log in again."
      : payload.detail || `Request failed with status ${response.status}`;
    return new ApiError(message, response.status);
  } catch {
    const text = await response.text();
    return new ApiError(text || `Request failed with status ${response.status}`, response.status);
  }
}

function withTimeout(init?: RequestInit): { init: RequestInit; cleanup: () => void } {
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  return {
    init: { ...init, signal: controller.signal },
    cleanup: () => globalThis.clearTimeout(timeoutId),
  };
}

async function request<T>(path: string, parser: (payload: unknown) => T, init?: RequestInit): Promise<T> {
  const { init: timedInit, cleanup } = withTimeout(init);
  const token = getAuthToken();
  try {
    const response = await fetch(buildUrl(path), {
      ...timedInit,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });

    if (!response.ok) {
      const error = await parseError(response);
      if (response.status === 401) {
        logout();
      }
      throw error;
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new ApiError("The backend returned malformed JSON.", response.status);
    }

    return parser(payload);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The backend request timed out. Please try again.", 408);
    }
    throw new ApiError("The backend is unavailable right now. Please try again.", 0);
  } finally {
    cleanup();
  }
}

function parseDocumentSummary(payload: unknown): DocumentSummary {
  if (!isObject(payload)) {
    throw new ApiError("Malformed document response from backend.", 500);
  }
  return {
    id: asNumber(payload.id),
    workspace_id: typeof payload.workspace_id === "number" ? payload.workspace_id : null,
    title: asString(payload.title),
    file_name: asString(payload.file_name),
    file_type: asString(payload.file_type),
    authors: asStringArray(payload.authors),
    year: typeof payload.year === "number" ? payload.year : null,
    abstract: asNullableString(payload.abstract),
    keywords: asStringArray(payload.keywords),
    chunk_count: asNumber(payload.chunk_count),
    uploaded_at: asString(payload.uploaded_at),
    last_indexed_at: asNullableString(payload.last_indexed_at),
    checksum: asString(payload.checksum),
    status: asDocumentStatus(payload.status),
    status_message: asNullableString(payload.status_message),
    page_count: typeof payload.page_count === "number" ? payload.page_count : null,
    progress: asNumber(payload.progress),
    task_id: asNullableString(payload.task_id),
    error_message: asNullableString(payload.error_message),
    indexed_at: asNullableString(payload.indexed_at),
    source_type: asString(payload.source_type, "upload"),
    source_url: asNullableString(payload.source_url),
  };
}

function parseSearchResponse(payload: unknown): SearchResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed search response from backend.", 500);
  }

  const rawResults = Array.isArray(payload.results) ? payload.results : [];
  return {
    query: asString(payload.query),
    total: asNumber(payload.total, rawResults.length),
    warnings: asStringArray(payload.warnings),
    results: rawResults
      .filter(isObject)
      .map((item) => ({
        chunk_id: asNumber(item.chunk_id),
        document_id: asNumber(item.document_id),
        document_title: asString(item.document_title),
        chunk_index: asNumber(item.chunk_index),
        page_number: typeof item.page_number === "number" ? item.page_number : null,
        score: asNumber(item.score),
        keyword_score: typeof item.keyword_score === "number" ? item.keyword_score : null,
        semantic_score: typeof item.semantic_score === "number" ? item.semantic_score : null,
        snippet: asString(item.snippet),
        highlighted_snippet: asString(item.highlighted_snippet, asString(item.snippet)),
        raw_text: asString(item.raw_text),
        matched_terms: asStringArray(item.matched_terms),
        retrieval_mode: asSearchMode(item.retrieval_mode),
        rerank_score: typeof item.rerank_score === "number" ? item.rerank_score : null,
        rerank_reasons: asStringArray(item.rerank_reasons),
        original_rank: typeof item.original_rank === "number" ? item.original_rank : null,
        final_rank: typeof item.final_rank === "number" ? item.final_rank : null,
        source_url: asNullableString(item.source_url),
        explanation: isObject(item.explanation)
          ? {
              keyword_overlap: asStringArray(item.explanation.keyword_overlap),
              semantic_match: asBoolean(item.explanation.semantic_match),
              title_match: asBoolean(item.explanation.title_match),
              keyword_score: typeof item.explanation.keyword_score === "number" ? item.explanation.keyword_score : null,
              semantic_score: typeof item.explanation.semantic_score === "number" ? item.explanation.semantic_score : null,
              hybrid_score: typeof item.explanation.hybrid_score === "number" ? item.explanation.hybrid_score : null,
              title_boost_applied: asBoolean(item.explanation.title_boost_applied),
              score_breakdown: asStringArray(item.explanation.score_breakdown),
              summary: asString(item.explanation.summary),
            }
          : {
              keyword_overlap: [],
              semantic_match: false,
              title_match: false,
              keyword_score: null,
              semantic_score: null,
              hybrid_score: null,
              title_boost_applied: false,
              score_breakdown: [],
              summary: "No explanation returned.",
            },
      })),
  };
}

function parseAskResponse(payload: unknown): AskResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed answer response from backend.", 500);
  }
  const citations = Array.isArray(payload.citations) ? payload.citations : [];
  const supportingChunks = parseSearchResponse({
    query: asString(payload.retrieval_query),
    total: Array.isArray(payload.supporting_chunks) ? payload.supporting_chunks.length : 0,
    results: Array.isArray(payload.supporting_chunks) ? payload.supporting_chunks : [],
    warnings: payload.warnings,
  }).results;

  return {
    answer: asString(payload.answer),
    retrieval_query: asString(payload.retrieval_query),
    grounded: asBoolean(payload.grounded),
    answer_source: asAnswerSource(payload.answer_source),
    evidence_strength: asEvidenceStrength(payload.evidence_strength),
    evidence_score: asNumber(payload.evidence_score),
    evidence_reasons: asStringArray(payload.evidence_reasons),
    evidence_warnings: asStringArray(payload.evidence_warnings),
    claim_verifications: Array.isArray(payload.claim_verifications)
      ? payload.claim_verifications.filter(isObject).map((item) => ({
          claim: asString(item.claim),
          status: asClaimStatus(item.status),
          confidence: asNumber(item.confidence),
          evidence_chunk_ids: Array.isArray(item.evidence_chunk_ids)
            ? item.evidence_chunk_ids.filter((chunkId): chunkId is number => typeof chunkId === "number")
            : [],
          evidence_snippets: asStringArray(item.evidence_snippets),
          reason: asString(item.reason),
        }))
      : [],
    why_this_answer: isObject(payload.why_this_answer)
      ? {
          answer_source: asAnswerSource(payload.why_this_answer.answer_source),
          evidence_strength: asEvidenceStrength(payload.why_this_answer.evidence_strength),
          used_chunks: Array.isArray(payload.why_this_answer.used_chunks)
            ? payload.why_this_answer.used_chunks.filter(isObject).map((item) => ({
                chunk_id: asNumber(item.chunk_id),
                document_id: asNumber(item.document_id),
                document_title: asString(item.document_title),
                chunk_index: asNumber(item.chunk_index),
                page_number: typeof item.page_number === "number" ? item.page_number : null,
                score: asNumber(item.score),
                reason: asString(item.reason),
              }))
            : [],
          summary: asString(payload.why_this_answer.summary),
        }
      : {
          answer_source: "extractive_fallback",
          evidence_strength: "weak",
          used_chunks: [],
          summary: "No answer provenance was returned.",
        },
    insufficient_evidence: asBoolean(payload.insufficient_evidence),
    warnings: asStringArray(payload.warnings),
    citations: citations.filter(isObject).map(parseCitation),
    supporting_chunks: supportingChunks,
  };
}

function parseCitation(payload: Record<string, unknown>): Citation {
  return {
    chunk_id: asNumber(payload.chunk_id),
    document_id: asNumber(payload.document_id),
    document_title: asString(payload.document_title),
    chunk_index: asNumber(payload.chunk_index),
    chunk_text_snippet: asString(payload.chunk_text_snippet),
    supporting_chunk_text: asString(payload.supporting_chunk_text),
    highlighted_snippet: asString(payload.highlighted_snippet, asString(payload.chunk_text_snippet)),
    matched_terms: asStringArray(payload.matched_terms),
    explanation_summary: asString(payload.explanation_summary),
    page_number: typeof payload.page_number === "number" ? payload.page_number : null,
    before_context: asNullableString(payload.before_context),
    after_context: asNullableString(payload.after_context),
    source_url: asNullableString(payload.source_url),
  };
}

function parseCompareResponse(payload: unknown): CompareResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed comparison response from backend.", 500);
  }
  const parsePoint = (item: Record<string, unknown>) => ({
    text: asString(item.text),
    document_ids: Array.isArray(item.document_ids)
      ? item.document_ids.filter((documentId): documentId is number => typeof documentId === "number")
      : [],
    supporting_chunk_ids: Array.isArray(item.supporting_chunk_ids)
      ? item.supporting_chunk_ids.filter((chunkId): chunkId is number => typeof chunkId === "number")
      : [],
    confidence: asNumber(item.confidence),
    type: asComparisonPointType(item.type),
  });

  return {
    comparison_summary: asString(payload.comparison_summary),
    agreements: Array.isArray(payload.agreements) ? payload.agreements.filter(isObject).map(parsePoint) : [],
    differences: Array.isArray(payload.differences) ? payload.differences.filter(isObject).map(parsePoint) : [],
    unique_points: Array.isArray(payload.unique_points) ? payload.unique_points.filter(isObject).map(parsePoint) : [],
    citations: Array.isArray(payload.citations) ? payload.citations.filter(isObject).map(parseCitation) : [],
    evidence_strength: asEvidenceStrength(payload.evidence_strength),
    evidence_score: asNumber(payload.evidence_score),
    evidence_reasons: asStringArray(payload.evidence_reasons),
    evidence_warnings: asStringArray(payload.evidence_warnings),
    warnings: asStringArray(payload.warnings),
  };
}

function parseStatsSummary(payload: unknown): StatsSummary {
  if (!isObject(payload)) {
    throw new ApiError("Malformed stats response from backend.", 500);
  }
  return {
    document_count: asNumber(payload.document_count),
    indexed_document_count: asNumber(payload.indexed_document_count),
    chunk_count: asNumber(payload.chunk_count),
    last_indexed_at: asNullableString(payload.last_indexed_at),
  };
}

function parseHealthResponse(payload: unknown): HealthResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed health response from backend.", 500);
  }
  return {
    status: asString(payload.status, "error"),
    database_ready: asBoolean(payload.database_ready),
    uploads_path: asString(payload.uploads_path),
    index_path: asString(payload.index_path),
    embedding_model: asString(payload.embedding_model),
    embedding_model_ready: asBoolean(payload.embedding_model_ready),
  };
}

function parseHealthDetailedResponse(payload: unknown): HealthDetailedResponse {
  const base = parseHealthResponse(payload);
  if (!isObject(payload)) {
    throw new ApiError("Malformed detailed health response from backend.", 500);
  }
  return {
    ...base,
    environment: asString(payload.environment),
    database_path: asString(payload.database_path),
    temp_path: asString(payload.temp_path),
    cors_origins: asStringArray(payload.cors_origins),
    cors_origin_regex: asNullableString(payload.cors_origin_regex),
    bm25_ready: asBoolean(payload.bm25_ready),
    faiss_index_present: asBoolean(payload.faiss_index_present),
    semantic_search_ready: asBoolean(payload.semantic_search_ready),
    embedding_model_status: asString(payload.embedding_model_status),
    llm_configured: asBoolean(payload.llm_configured),
  };
}

function parseUploadResponse(payload: unknown): UploadResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed upload response from backend.", 500);
  }
  const documents = Array.isArray(payload.documents) ? payload.documents.map(parseDocumentSummary) : [];
  return {
    message: asString(payload.message),
    documents,
    duplicates_skipped: asNumber(payload.duplicates_skipped),
    failures: asStringArray(payload.failures),
    task_ids: asStringArray(payload.task_ids),
    indexing_mode: asString(payload.indexing_mode, "synchronous"),
    warnings: asStringArray(payload.warnings),
  };
}

function parseTaskSummary(payload: unknown): TaskSummary {
  if (!isObject(payload)) {
    throw new ApiError("Malformed task response from backend.", 500);
  }
  return {
    task_id: asString(payload.task_id),
    document_id: asNumber(payload.document_id),
    workspace_id: typeof payload.workspace_id === "number" ? payload.workspace_id : null,
    status: asTaskStatus(payload.status),
    progress: asNumber(payload.progress),
    error_message: asNullableString(payload.error_message),
    created_at: asString(payload.created_at),
    updated_at: asString(payload.updated_at),
    completed_at: asNullableString(payload.completed_at),
    indexing_mode: asString(payload.indexing_mode, "synchronous"),
  };
}

function parseEvaluationSummary(payload: unknown): EvaluationSummary {
  if (!isObject(payload)) {
    throw new ApiError("Malformed evaluation summary from backend.", 500);
  }
  return {
    dataset_size: asNumber(payload.dataset_size),
    corpus_document_count: asNumber(payload.corpus_document_count),
    top_k_recall: asNumber(payload.top_k_recall),
    citation_match_rate: asNumber(payload.citation_match_rate),
    unsupported_claim_rate: asNumber(payload.unsupported_claim_rate),
    average_evidence_score: asNumber(payload.average_evidence_score),
    groundedness_score: asNumber(payload.groundedness_score),
    average_answer_latency_ms: asNumber(payload.average_answer_latency_ms),
    average_search_latency_ms: asNumber(payload.average_search_latency_ms),
    warnings: asStringArray(payload.warnings),
    ran_at: asNullableString(payload.ran_at),
  };
}

function parseEvaluationRun(payload: unknown): EvaluationRunResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed evaluation response from backend.", 500);
  }
  return {
    summary: parseEvaluationSummary(payload.summary),
    results: Array.isArray(payload.results)
      ? payload.results.filter(isObject).map((item) => ({
          question: asString(item.question),
          top_k_recall: asNumber(item.top_k_recall),
          citation_match_rate: asNumber(item.citation_match_rate),
          unsupported_claim_rate: asNumber(item.unsupported_claim_rate),
          average_evidence_score: asNumber(item.average_evidence_score),
          groundedness_score: asNumber(item.groundedness_score),
          answer_latency_ms: asNumber(item.answer_latency_ms),
          search_latency_ms: asNumber(item.search_latency_ms),
          matched_terms: asStringArray(item.matched_terms),
          matched_document_titles: asStringArray(item.matched_document_titles),
          expected_document_titles: asStringArray(item.expected_document_titles),
          expected_citation_chunk_ids: Array.isArray(item.expected_citation_chunk_ids)
            ? item.expected_citation_chunk_ids.filter((id): id is number => typeof id === "number")
            : [],
          returned_citation_chunk_ids: Array.isArray(item.returned_citation_chunk_ids)
            ? item.returned_citation_chunk_ids.filter((id): id is number => typeof id === "number")
            : [],
          warnings: asStringArray(item.warnings),
        }))
      : [],
  };
}

function parseSystemMetrics(payload: unknown): SystemMetrics {
  if (!isObject(payload)) {
    throw new ApiError("Malformed system metrics response from backend.", 500);
  }
  return {
    search_latency_ms: asNumber(payload.search_latency_ms),
    ask_latency_ms: asNumber(payload.ask_latency_ms),
    indexing_latency_ms: asNumber(payload.indexing_latency_ms),
    failed_indexing_count: asNumber(payload.failed_indexing_count),
    total_documents_indexed: asNumber(payload.total_documents_indexed),
    total_chunks_indexed: asNumber(payload.total_chunks_indexed),
    warnings: asStringArray(payload.warnings),
  };
}

function parseWorkspaceSummary(payload: unknown): WorkspaceSummary {
  if (!isObject(payload)) {
    throw new ApiError("Malformed workspace response from backend.", 500);
  }
  return {
    id: asNumber(payload.id),
    name: asString(payload.name),
    slug: asString(payload.slug),
    role: asWorkspaceRole(payload.role),
    created_at: asString(payload.created_at),
  };
}

function parseWorkspaceDetail(payload: unknown): WorkspaceDetail {
  const base = parseWorkspaceSummary(payload);
  if (!isObject(payload)) {
    throw new ApiError("Malformed workspace response from backend.", 500);
  }
  return {
    ...base,
    members: Array.isArray(payload.members)
      ? payload.members.filter(isObject).map((member) => ({
          user_id: asNumber(member.user_id),
          name: asString(member.name),
          email: asString(member.email),
          role: asWorkspaceRole(member.role),
        }))
      : [],
  };
}

function parseEvalSet(payload: unknown): EvalSetPublic {
  if (!isObject(payload)) {
    throw new ApiError("Malformed evaluation set response from backend.", 500);
  }
  return {
    id: asNumber(payload.id),
    workspace_id: asNumber(payload.workspace_id),
    name: asString(payload.name),
    description: asNullableString(payload.description),
    created_at: asString(payload.created_at),
    questions: Array.isArray(payload.questions)
      ? payload.questions.filter(isObject).map((question) => ({
          id: asNumber(question.id),
          eval_set_id: asNumber(question.eval_set_id),
          workspace_id: asNumber(question.workspace_id),
          question: asString(question.question),
          expected_answer: asNullableString(question.expected_answer),
          expected_terms: asStringArray(question.expected_terms),
          expected_document_ids: Array.isArray(question.expected_document_ids)
            ? question.expected_document_ids.filter((id): id is number => typeof id === "number")
            : [],
          expected_citation_chunk_ids: Array.isArray(question.expected_citation_chunk_ids)
            ? question.expected_citation_chunk_ids.filter((id): id is number => typeof id === "number")
            : [],
          created_at: asString(question.created_at),
          updated_at: asString(question.updated_at),
        }))
      : [],
  };
}

function parseEvalRun(payload: unknown): EvalRunPublic {
  if (!isObject(payload)) {
    throw new ApiError("Malformed evaluation run response from backend.", 500);
  }
  return {
    id: asNumber(payload.id),
    eval_set_id: asNumber(payload.eval_set_id),
    workspace_id: asNumber(payload.workspace_id),
    summary: parseEvaluationSummary(payload.summary),
    results: parseEvaluationRun({ summary: payload.summary, results: payload.results }).results,
    created_at: asString(payload.created_at),
  };
}

function parseRetrievalPlayground(payload: unknown): RetrievalPlaygroundResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed retrieval playground response from backend.", 500);
  }
  return {
    query: asString(payload.query),
    pipelines: Array.isArray(payload.pipelines)
      ? payload.pipelines.filter(isObject).map((item) => ({
          pipeline: asRetrievalPipelineName(item.pipeline),
          results: parseSearchResponse({ query: payload.query, results: item.results, total: 0, warnings: item.warnings }).results,
          latency_ms: asNumber(item.latency_ms),
          warnings: asStringArray(item.warnings),
        }))
      : [],
  };
}

function parseIndexStatus(payload: unknown): IndexStatusResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed index status response from backend.", 500);
  }
  return {
    workspace_id: asNumber(payload.workspace_id),
    document_count: asNumber(payload.document_count),
    indexed_document_count: asNumber(payload.indexed_document_count),
    chunk_count: asNumber(payload.chunk_count),
    failed_tasks: asNumber(payload.failed_tasks),
    queue_mode: asString(payload.queue_mode),
    redis_available: asBoolean(payload.redis_available),
    warnings: asStringArray(payload.warnings),
  };
}

function parseIndexLog(payload: unknown): IndexLogEntry {
  if (!isObject(payload)) {
    throw new ApiError("Malformed index log response from backend.", 500);
  }
  return {
    id: asNumber(payload.id),
    workspace_id: asNumber(payload.workspace_id),
    document_id: typeof payload.document_id === "number" ? payload.document_id : null,
    level: asString(payload.level),
    message: asString(payload.message),
    created_at: asString(payload.created_at),
  };
}

function parseConnectorImport(payload: unknown): ConnectorImportResponse {
  if (!isObject(payload)) {
    throw new ApiError("Malformed connector response from backend.", 500);
  }
  return {
    document: parseDocumentSummary(payload.document),
    task_id: asNullableString(payload.task_id),
    indexing_mode: asString(payload.indexing_mode, "synchronous"),
    warnings: asStringArray(payload.warnings),
  };
}

function parseAdminObservability(payload: unknown): AdminObservabilityResponse {
  const metrics = parseSystemMetrics(payload);
  if (!isObject(payload)) {
    throw new ApiError("Malformed observability response from backend.", 500);
  }
  return {
    ...metrics,
    queue_mode: asString(payload.queue_mode),
    redis_available: asBoolean(payload.redis_available),
    document_count: asNumber(payload.document_count),
    chunk_count: asNumber(payload.chunk_count),
    evaluation_runs: asNumber(payload.evaluation_runs),
    task_failure_count: asNumber(payload.task_failure_count),
  };
}

function parseApiKey(payload: unknown): ApiKeyPublic {
  if (!isObject(payload)) {
    throw new ApiError("Malformed API key response from backend.", 500);
  }
  return {
    id: asNumber(payload.id),
    workspace_id: asNumber(payload.workspace_id),
    name: asString(payload.name),
    prefix: asString(payload.prefix),
    created_at: asString(payload.created_at),
    last_used_at: asNullableString(payload.last_used_at),
    api_key: asNullableString(payload.api_key),
  };
}

export async function fetchDocuments(): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>("/documents", (payload) => {
    if (!Array.isArray(payload)) {
      throw new ApiError("Malformed documents response from backend.", 500);
    }
    return payload.map(parseDocumentSummary);
  });
}

export async function fetchDocumentStats(): Promise<StatsSummary> {
  return request<StatsSummary>("/documents/stats/summary", parseStatsSummary);
}

export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health", parseHealthResponse);
}

export async function fetchDetailedHealth(): Promise<HealthDetailedResponse> {
  return request<HealthDetailedResponse>("/health/detailed", parseHealthDetailedResponse);
}

export async function fetchTask(taskId: string): Promise<TaskSummary> {
  return request<TaskSummary>(`/tasks/${encodeURIComponent(taskId)}`, parseTaskSummary);
}

export async function fetchSystemMetrics(): Promise<SystemMetrics> {
  return request<SystemMetrics>("/metrics/system", parseSystemMetrics);
}

export async function runEvaluation(): Promise<EvaluationRunResponse> {
  return request<EvaluationRunResponse>("/evaluation/run", parseEvaluationRun);
}

export async function fetchEvaluationSummary(): Promise<EvaluationSummary> {
  return request<EvaluationSummary>("/evaluation/summary", parseEvaluationSummary);
}

export async function fetchWorkspaces(): Promise<WorkspaceSummary[]> {
  return request<WorkspaceSummary[]>("/workspaces", (payload) => Array.isArray(payload) ? payload.map(parseWorkspaceSummary) : []);
}

export async function createWorkspace(name: string): Promise<WorkspaceSummary> {
  return request<WorkspaceSummary>("/workspaces", parseWorkspaceSummary, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

export async function fetchWorkspace(workspaceId: number): Promise<WorkspaceDetail> {
  return request<WorkspaceDetail>(`/workspaces/${workspaceId}`, parseWorkspaceDetail);
}

export async function addWorkspaceMember(workspaceId: number, email: string, role: WorkspaceRole): Promise<WorkspaceDetail> {
  return request<WorkspaceDetail>(`/workspaces/${workspaceId}/members`, parseWorkspaceDetail, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, role }),
  });
}

export async function fetchEvalSets(workspaceId?: number): Promise<EvalSetPublic[]> {
  const suffix = workspaceId ? `?workspace_id=${workspaceId}` : "";
  return request<EvalSetPublic[]>(`/evaluation/sets${suffix}`, (payload) => Array.isArray(payload) ? payload.map(parseEvalSet) : []);
}

export async function createEvalSet(name: string, description: string, workspaceId?: number): Promise<EvalSetPublic> {
  return request<EvalSetPublic>("/evaluation/sets", parseEvalSet, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description, workspace_id: workspaceId ?? null }),
  });
}

export async function addEvalQuestion(evalSetId: number, question: string, expectedTerms: string[]): Promise<EvalSetPublic> {
  await request(`/evaluation/sets/${evalSetId}/questions`, (payload) => payload, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, expected_terms: expectedTerms }),
  });
  return request<EvalSetPublic>(`/evaluation/sets/${evalSetId}`, parseEvalSet);
}

export async function runEvalSet(evalSetId: number): Promise<EvalRunPublic> {
  return request<EvalRunPublic>(`/evaluation/sets/${evalSetId}/run`, parseEvalRun, { method: "POST" });
}

export async function runRetrievalPlayground(query: string, pipelines: RetrievalPipelineName[], workspaceId?: number): Promise<RetrievalPlaygroundResponse> {
  return request<RetrievalPlaygroundResponse>("/retrieval/playground", parseRetrievalPlayground, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, pipelines, top_k: 5, workspace_id: workspaceId ?? null }),
  });
}

export async function fetchIndexStatus(workspaceId: number): Promise<IndexStatusResponse> {
  return request<IndexStatusResponse>(`/workspaces/${workspaceId}/index/status`, parseIndexStatus);
}

export async function fetchIndexLogs(workspaceId: number): Promise<IndexLogEntry[]> {
  return request<IndexLogEntry[]>(`/workspaces/${workspaceId}/index/logs`, (payload) => Array.isArray(payload) ? payload.map(parseIndexLog) : []);
}

export async function reindexDocument(documentId: number): Promise<DocumentSummary> {
  return request<DocumentSummary>(`/documents/${documentId}/reindex`, parseDocumentSummary, { method: "POST" });
}

export async function deleteDocument(documentId: number): Promise<void> {
  await request(`/documents/${documentId}`, (payload) => payload, { method: "DELETE" });
}

export async function rebuildWorkspaceIndex(workspaceId: number): Promise<IndexStatusResponse> {
  return request<IndexStatusResponse>(`/workspaces/${workspaceId}/index/rebuild`, parseIndexStatus, { method: "POST" });
}

export async function importWebUrl(url: string, workspaceId?: number): Promise<ConnectorImportResponse> {
  return request<ConnectorImportResponse>("/connectors/web-url/import", parseConnectorImport, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, workspace_id: workspaceId ?? null }),
  });
}

export async function fetchAdminObservability(): Promise<AdminObservabilityResponse> {
  return request<AdminObservabilityResponse>("/admin/observability", parseAdminObservability);
}

export async function createApiKey(name: string, workspaceId?: number): Promise<ApiKeyPublic> {
  return request<ApiKeyPublic>("/api-keys", parseApiKey, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, workspace_id: workspaceId ?? null }),
  });
}

export async function fetchApiKeys(workspaceId?: number): Promise<ApiKeyPublic[]> {
  const suffix = workspaceId ? `?workspace_id=${workspaceId}` : "";
  return request<ApiKeyPublic[]>(`/api-keys${suffix}`, (payload) => Array.isArray(payload) ? payload.map(parseApiKey) : []);
}

export async function deleteApiKey(keyId: number): Promise<void> {
  await request(`/api-keys/${keyId}`, (payload) => payload, { method: "DELETE" });
}

export function uploadDocuments(
  files: File[],
  onProgress?: (percent: number) => void,
  workspaceId?: number,
): Promise<UploadResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  if (workspaceId) {
    formData.append("workspace_id", String(workspaceId));
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", buildUrl("/documents/upload"));
    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    xhr.responseType = "json";
    xhr.timeout = REQUEST_TIMEOUT_MS;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100);
        try {
          resolve(parseUploadResponse(xhr.response));
        } catch (error) {
          reject(error);
        }
        return;
      }
      const payload = xhr.response as ApiErrorResponse | null;
      if (xhr.status === 401) {
        logout();
      }
      reject(new ApiError(payload?.detail || "Upload failed", xhr.status));
    };
    xhr.onerror = () => reject(new ApiError("Network error while uploading documents.", 0));
    xhr.ontimeout = () => reject(new ApiError("The upload timed out. Please try again.", 408));
    xhr.send(formData);
  });
}

export async function runSearch(
  mode: SearchMode,
  query: string,
  limit = 8,
  documentId?: number,
): Promise<SearchResponse> {
  return request<SearchResponse>(`/search/${mode}`, parseSearchResponse, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, limit, document_id: documentId ?? null }),
  });
}

export async function askResearchMind(
  question: string,
  limit = 6,
  documentId?: number,
): Promise<AskResponse> {
  return request<AskResponse>("/ask", parseAskResponse, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, limit, document_id: documentId ?? null }),
  });
}

export async function compareDocuments(documentIds: number[], question?: string): Promise<CompareResponse> {
  return request<CompareResponse>("/compare", parseCompareResponse, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ document_ids: documentIds, question: question?.trim() || null }),
  });
}
