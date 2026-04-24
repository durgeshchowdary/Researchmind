import time

from app.models.schemas import RetrievalPipelineResult, RetrievalPlaygroundRequest, RetrievalPlaygroundResponse, SearchRequest
from app.services.search_service import search_service
from app.services.workspace_service import workspace_service


class RetrievalPlaygroundService:
    def run(self, payload: RetrievalPlaygroundRequest, user_id: int) -> RetrievalPlaygroundResponse:
        workspace_id = workspace_service.resolve_workspace_id(user_id, payload.workspace_id)
        pipeline_results: list[RetrievalPipelineResult] = []
        for pipeline in payload.pipelines:
            started = time.perf_counter()
            request = SearchRequest(query=payload.query, limit=payload.top_k, workspace_id=workspace_id)
            if pipeline == "bm25":
                response = search_service.keyword_search(request, user_id)
            elif pipeline == "semantic":
                response = search_service.semantic_search(request, user_id)
            else:
                response = search_service.hybrid_search(request, user_id)
                if pipeline == "hybrid":
                    for result in response.results:
                        result.rerank_score = None
                        result.rerank_reasons = []
                        result.original_rank = None
                        result.final_rank = None
            pipeline_results.append(
                RetrievalPipelineResult(
                    pipeline=pipeline,
                    results=response.results,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    warnings=response.warnings,
                )
            )
        return RetrievalPlaygroundResponse(query=payload.query, pipelines=pipeline_results)


retrieval_playground_service = RetrievalPlaygroundService()
