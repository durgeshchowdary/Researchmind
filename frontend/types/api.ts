export type DocumentStatus = "uploaded" | "queued" | "processing" | "extracted" | "chunked" | "indexed" | "failed";
export type TaskStatus = "queued" | "processing" | "chunked" | "indexed" | "failed";
export type SearchMode = "keyword" | "semantic" | "hybrid";
export type WorkspaceRole = "owner" | "editor" | "viewer";
export type RetrievalPipelineName = "bm25" | "semantic" | "hybrid" | "hybrid_reranked";
export type AnswerSource = "llm" | "extractive_fallback" | "insufficient_evidence";
export type EvidenceStrength = "strong" | "medium" | "weak" | "insufficient";
export type ClaimStatus = "supported" | "partially_supported" | "unsupported";
export type ComparisonPointType = "agreement" | "difference" | "unique";

export type ApiErrorResponse = {
  detail: string;
};

export type AuthUser = {
  id: number;
  name: string;
  email: string;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type DocumentSummary = {
  id: number;
  workspace_id: number | null;
  title: string;
  file_name: string;
  file_type: string;
  authors: string[];
  year: number | null;
  abstract: string | null;
  keywords: string[];
  chunk_count: number;
  uploaded_at: string;
  last_indexed_at: string | null;
  checksum: string;
  status: DocumentStatus;
  status_message: string | null;
  page_count: number | null;
  progress: number;
  task_id: string | null;
  error_message: string | null;
  indexed_at: string | null;
  source_type: string;
  source_url: string | null;
};

export type ChunkRecord = {
  id: number;
  document_id: number;
  workspace_id: number | null;
  chunk_index: number;
  text: string;
  token_count: number;
  page_number: number | null;
};

export type DocumentDetail = DocumentSummary & {
  chunks: ChunkRecord[];
};

export type UploadResponse = {
  message: string;
  documents: DocumentSummary[];
  duplicates_skipped: number;
  failures: string[];
  task_ids: string[];
  indexing_mode: string;
  warnings: string[];
};

export type TaskSummary = {
  task_id: string;
  document_id: number;
  workspace_id: number | null;
  status: TaskStatus;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  indexing_mode: string;
};

export type SearchExplanation = {
  keyword_overlap: string[];
  semantic_match: boolean;
  title_match: boolean;
  keyword_score: number | null;
  semantic_score: number | null;
  hybrid_score: number | null;
  title_boost_applied: boolean;
  score_breakdown: string[];
  summary: string;
};

export type SearchResult = {
  chunk_id: number;
  document_id: number;
  document_title: string;
  chunk_index: number;
  page_number: number | null;
  score: number;
  keyword_score: number | null;
  semantic_score: number | null;
  snippet: string;
  highlighted_snippet: string;
  raw_text: string;
  matched_terms: string[];
  retrieval_mode: SearchMode;
  explanation: SearchExplanation;
  rerank_score: number | null;
  rerank_reasons: string[];
  original_rank: number | null;
  final_rank: number | null;
  source_url: string | null;
};

export type SearchResponse = {
  query: string;
  total: number;
  results: SearchResult[];
  warnings: string[];
};

export type Citation = {
  chunk_id: number;
  document_id: number;
  document_title: string;
  chunk_index: number;
  chunk_text_snippet: string;
  supporting_chunk_text: string;
  highlighted_snippet: string;
  matched_terms: string[];
  explanation_summary: string;
  page_number: number | null;
  before_context: string | null;
  after_context: string | null;
  source_url: string | null;
};

export type WhyAnswerChunk = {
  chunk_id: number;
  document_id: number;
  document_title: string;
  chunk_index: number;
  page_number: number | null;
  score: number;
  reason: string;
};

export type WhyAnswerSummary = {
  answer_source: AnswerSource;
  evidence_strength: EvidenceStrength;
  used_chunks: WhyAnswerChunk[];
  summary: string;
};

export type ClaimVerification = {
  claim: string;
  status: ClaimStatus;
  confidence: number;
  evidence_chunk_ids: number[];
  evidence_snippets: string[];
  reason: string;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
  retrieval_query: string;
  grounded: boolean;
  answer_source: AnswerSource;
  evidence_strength: EvidenceStrength;
  evidence_score: number;
  evidence_reasons: string[];
  evidence_warnings: string[];
  claim_verifications: ClaimVerification[];
  why_this_answer: WhyAnswerSummary;
  insufficient_evidence: boolean;
  supporting_chunks: SearchResult[];
  warnings: string[];
};

export type CompareRequest = {
  document_ids: number[];
  question?: string | null;
};

export type ComparisonPoint = {
  text: string;
  document_ids: number[];
  supporting_chunk_ids: number[];
  confidence: number;
  type: ComparisonPointType;
};

export type CompareResponse = {
  comparison_summary: string;
  agreements: ComparisonPoint[];
  differences: ComparisonPoint[];
  unique_points: ComparisonPoint[];
  citations: Citation[];
  evidence_strength: EvidenceStrength;
  evidence_score: number;
  evidence_reasons: string[];
  evidence_warnings: string[];
  warnings: string[];
};

export type StatsSummary = {
  document_count: number;
  indexed_document_count: number;
  chunk_count: number;
  last_indexed_at: string | null;
};

export type HealthResponse = {
  status: string;
  database_ready: boolean;
  uploads_path: string;
  index_path: string;
  embedding_model: string;
  embedding_model_ready: boolean;
};

export type HealthDetailedResponse = HealthResponse & {
  environment: string;
  database_path: string;
  temp_path: string;
  cors_origins: string[];
  cors_origin_regex: string | null;
  bm25_ready: boolean;
  faiss_index_present: boolean;
  semantic_search_ready: boolean;
  embedding_model_status: string;
  llm_configured: boolean;
};

export type EvaluationQuestionResult = {
  question: string;
  top_k_recall: number;
  citation_match_rate: number;
  unsupported_claim_rate: number;
  average_evidence_score: number;
  groundedness_score: number;
  answer_latency_ms: number;
  search_latency_ms: number;
  matched_terms: string[];
  matched_document_titles: string[];
  expected_document_titles: string[];
  expected_citation_chunk_ids: number[];
  returned_citation_chunk_ids: number[];
  warnings: string[];
};

export type EvaluationSummary = {
  dataset_size: number;
  corpus_document_count: number;
  top_k_recall: number;
  citation_match_rate: number;
  unsupported_claim_rate: number;
  average_evidence_score: number;
  groundedness_score: number;
  average_answer_latency_ms: number;
  average_search_latency_ms: number;
  warnings: string[];
  ran_at: string | null;
};

export type EvaluationRunResponse = {
  summary: EvaluationSummary;
  results: EvaluationQuestionResult[];
};

export type SystemMetrics = {
  search_latency_ms: number;
  ask_latency_ms: number;
  indexing_latency_ms: number;
  failed_indexing_count: number;
  total_documents_indexed: number;
  total_chunks_indexed: number;
  warnings: string[];
};

export type WorkspaceMember = {
  user_id: number;
  name: string;
  email: string;
  role: WorkspaceRole;
};

export type WorkspaceSummary = {
  id: number;
  name: string;
  slug: string;
  role: WorkspaceRole;
  created_at: string;
};

export type WorkspaceDetail = WorkspaceSummary & {
  members: WorkspaceMember[];
};

export type EvalQuestionPublic = {
  id: number;
  eval_set_id: number;
  workspace_id: number;
  question: string;
  expected_answer: string | null;
  expected_terms: string[];
  expected_document_ids: number[];
  expected_citation_chunk_ids: number[];
  created_at: string;
  updated_at: string;
};

export type EvalSetPublic = {
  id: number;
  workspace_id: number;
  name: string;
  description: string | null;
  created_at: string;
  questions: EvalQuestionPublic[];
};

export type EvalRunPublic = {
  id: number;
  eval_set_id: number;
  workspace_id: number;
  summary: EvaluationSummary;
  results: EvaluationQuestionResult[];
  created_at: string;
};

export type RetrievalPipelineResult = {
  pipeline: RetrievalPipelineName;
  results: SearchResult[];
  latency_ms: number;
  warnings: string[];
};

export type RetrievalPlaygroundResponse = {
  query: string;
  pipelines: RetrievalPipelineResult[];
};

export type IndexStatusResponse = {
  workspace_id: number;
  document_count: number;
  indexed_document_count: number;
  chunk_count: number;
  failed_tasks: number;
  queue_mode: string;
  redis_available: boolean;
  warnings: string[];
};

export type IndexLogEntry = {
  id: number;
  workspace_id: number;
  document_id: number | null;
  level: string;
  message: string;
  created_at: string;
};

export type ConnectorImportResponse = {
  document: DocumentSummary;
  task_id: string | null;
  indexing_mode: string;
  warnings: string[];
};

export type AdminObservabilityResponse = SystemMetrics & {
  queue_mode: string;
  redis_available: boolean;
  document_count: number;
  chunk_count: number;
  evaluation_runs: number;
  task_failure_count: number;
};

export type ApiKeyPublic = {
  id: number;
  workspace_id: number;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  api_key: string | null;
};
