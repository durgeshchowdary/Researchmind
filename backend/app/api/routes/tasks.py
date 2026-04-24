from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.models.schemas import TaskSummary, UserPublic
from app.services.task_service import task_service


router = APIRouter()


@router.get("", response_model=list[TaskSummary])
def list_tasks(current_user: UserPublic = Depends(get_current_user)) -> list[TaskSummary]:
    return task_service.list_tasks(current_user.id)


@router.get("/{task_id}", response_model=TaskSummary)
def get_task(task_id: str, current_user: UserPublic = Depends(get_current_user)) -> TaskSummary:
    task = task_service.get_task(task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task
