from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import (
    EvalQuestionCreateRequest,
    EvalQuestionPatchRequest,
    EvalQuestionPublic,
    EvalRunPublic,
    EvalSetCreateRequest,
    EvalSetPublic,
    EvaluationRunResponse,
    EvaluationSummary,
    UserPublic,
)
from app.services.evaluation_benchmark_service import evaluation_benchmark_service
from app.services.evaluation_dataset_service import evaluation_dataset_service


router = APIRouter()


@router.get("/run", response_model=EvaluationRunResponse)
async def run_evaluation(current_user: UserPublic = Depends(get_current_user)) -> EvaluationRunResponse:
    return await evaluation_benchmark_service.run(current_user.id)


@router.get("/summary", response_model=EvaluationSummary)
def evaluation_summary(_: UserPublic = Depends(get_current_user)) -> EvaluationSummary:
    return evaluation_benchmark_service.latest_summary()


@router.post("/sets", response_model=EvalSetPublic)
def create_eval_set(payload: EvalSetCreateRequest, current_user: UserPublic = Depends(get_current_user)) -> EvalSetPublic:
    return evaluation_dataset_service.create_set(payload, current_user.id)


@router.get("/sets", response_model=list[EvalSetPublic])
def list_eval_sets(workspace_id: int | None = None, current_user: UserPublic = Depends(get_current_user)) -> list[EvalSetPublic]:
    return evaluation_dataset_service.list_sets(current_user.id, workspace_id)


@router.get("/sets/{eval_set_id}", response_model=EvalSetPublic)
def get_eval_set(eval_set_id: int, current_user: UserPublic = Depends(get_current_user)) -> EvalSetPublic:
    return evaluation_dataset_service.get_set(eval_set_id, current_user.id)


@router.post("/sets/{eval_set_id}/questions", response_model=EvalQuestionPublic)
def add_eval_question(
    eval_set_id: int,
    payload: EvalQuestionCreateRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> EvalQuestionPublic:
    return evaluation_dataset_service.add_question(eval_set_id, payload, current_user.id)


@router.patch("/questions/{question_id}", response_model=EvalQuestionPublic)
def patch_eval_question(
    question_id: int,
    payload: EvalQuestionPatchRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> EvalQuestionPublic:
    return evaluation_dataset_service.patch_question(question_id, payload, current_user.id)


@router.delete("/questions/{question_id}")
def delete_eval_question(question_id: int, current_user: UserPublic = Depends(get_current_user)) -> dict[str, str]:
    return evaluation_dataset_service.delete_question(question_id, current_user.id)


@router.post("/sets/{eval_set_id}/run", response_model=EvalRunPublic)
async def run_eval_set(eval_set_id: int, current_user: UserPublic = Depends(get_current_user)) -> EvalRunPublic:
    return await evaluation_dataset_service.run_set(eval_set_id, current_user.id)


@router.get("/runs/{run_id}", response_model=EvalRunPublic)
def get_eval_run(run_id: int, current_user: UserPublic = Depends(get_current_user)) -> EvalRunPublic:
    return evaluation_dataset_service.get_run(run_id, current_user.id)


@router.get("/sets/{eval_set_id}/runs", response_model=list[EvalRunPublic])
def list_eval_runs(eval_set_id: int, current_user: UserPublic = Depends(get_current_user)) -> list[EvalRunPublic]:
    return evaluation_dataset_service.list_runs(eval_set_id, current_user.id)
