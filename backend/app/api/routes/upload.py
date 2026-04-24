from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.core.auth import get_current_user
from app.models.schemas import UploadResponse, UserPublic
from app.services.task_service import task_service


router = APIRouter()


@router.post("/papers", response_model=UploadResponse)
async def upload_papers(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    workspace_id: int | None = Form(default=None),
    current_user: UserPublic = Depends(get_current_user),
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")
    documents, duplicates_skipped, failures, task_ids, mode, warnings = await task_service.enqueue_uploads(
        files,
        current_user.id,
        background_tasks,
        workspace_id,
    )
    return UploadResponse(
        message=f"Processed {len(files)} file(s). Added {len(documents)} new paper(s).",
        documents=documents,
        duplicates_skipped=duplicates_skipped,
        failures=failures,
        task_ids=task_ids,
        indexing_mode=mode,
        warnings=warnings,
    )
