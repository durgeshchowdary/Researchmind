from fastapi import APIRouter, Depends, Header

from app.core.auth import get_current_user
from app.models.schemas import (
    ApiAnswerRequest,
    ApiEvaluateRequest,
    ApiKeyCreateRequest,
    ApiKeyPublic,
    ApiRetrieveRequest,
    ApiRerankRequest,
    AskRequest,
    AskResponse,
    EvaluationRunResponse,
    SearchRequest,
    SearchResponse,
    UserPublic,
)
from app.services.api_key_service import api_key_service
from app.services.rag_service import rag_service
from app.services.reranking_service import reranking_service
from app.services.search_service import search_service


router = APIRouter()


@router.post("/api-keys", response_model=ApiKeyPublic)
def create_api_key(payload: ApiKeyCreateRequest, current_user: UserPublic = Depends(get_current_user)) -> ApiKeyPublic:
    return api_key_service.create_key(payload, current_user.id)


@router.get("/api-keys", response_model=list[ApiKeyPublic])
def list_api_keys(workspace_id: int | None = None, current_user: UserPublic = Depends(get_current_user)) -> list[ApiKeyPublic]:
    return api_key_service.list_keys(current_user.id, workspace_id)


@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: int, current_user: UserPublic = Depends(get_current_user)) -> dict[str, str]:
    return api_key_service.delete_key(key_id, current_user.id)


def workspace_from_api_key(x_api_key: str = Header(alias="X-API-Key")) -> int:
    return api_key_service.authenticate(x_api_key)


@router.post("/api/retrieve", response_model=SearchResponse)
def api_retrieve(payload: ApiRetrieveRequest, workspace_id: int = Depends(workspace_from_api_key)) -> SearchResponse:
    return search_service.hybrid_search(SearchRequest(query=payload.query, limit=payload.limit, workspace_id=workspace_id), None)


@router.post("/api/rerank")
def api_rerank(payload: ApiRerankRequest, workspace_id: int = Depends(workspace_from_api_key)):
    results, warnings = reranking_service.rerank(payload.query, payload.results, len(payload.results))
    return {"workspace_id": workspace_id, "results": results, "warnings": warnings}


@router.post("/api/answer", response_model=AskResponse)
async def api_answer(payload: ApiAnswerRequest, workspace_id: int = Depends(workspace_from_api_key)) -> AskResponse:
    return await rag_service.answer_question(AskRequest(question=payload.question, limit=payload.limit, workspace_id=workspace_id), None)


@router.post("/api/evaluate", response_model=EvaluationRunResponse)
async def api_evaluate(payload: ApiEvaluateRequest, workspace_id: int = Depends(workspace_from_api_key)) -> EvaluationRunResponse:
    from app.services.evaluation_benchmark_service import evaluation_benchmark_service

    warning = "API evaluation currently runs supplied default cases only; use authenticated UI endpoints for saved eval sets."
    if payload.eval_set_id is not None:
        warning = f"Saved eval_set_id {payload.eval_set_id} requires user auth; returning an empty API-key scoped run."
    return await evaluation_benchmark_service.run_cases([], None, workspace_id, [warning])
