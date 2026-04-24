from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from app.core.auth import get_current_user
from app.models.schemas import DocumentDetail, DocumentSummary, StatsSummary, UploadResponse
from app.models.schemas import UserPublic
from app.services.document_service import document_service
from app.services.task_service import task_service
from app.services.workspace_service import workspace_service


router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
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
        message=f"Processed {len(files)} file(s). Added {len(documents)} new document(s).",
        documents=documents,
        duplicates_skipped=duplicates_skipped,
        failures=failures,
        task_ids=task_ids,
        indexing_mode=mode,
        warnings=warnings,
    )


@router.get("", response_model=list[DocumentSummary])
def list_documents(current_user: UserPublic = Depends(get_current_user)) -> list[DocumentSummary]:
    workspace_id = workspace_service.ensure_default_workspace(current_user).id
    return document_service.list_documents(current_user.id, workspace_id)


@router.get("/stats/summary", response_model=StatsSummary)
def get_stats(current_user: UserPublic = Depends(get_current_user)) -> StatsSummary:
    workspace_id = workspace_service.ensure_default_workspace(current_user).id
    return document_service.get_stats(current_user.id, workspace_id)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: int, current_user: UserPublic = Depends(get_current_user)) -> DocumentDetail:
    document = document_service.get_document_detail(document_id, current_user.id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document
