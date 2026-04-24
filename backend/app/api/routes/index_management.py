from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import DocumentSummary, IndexLogEntry, IndexStatusResponse, UserPublic
from app.services.index_management_service import index_management_service


router = APIRouter()


@router.post("/documents/{document_id}/reindex", response_model=DocumentSummary)
def reindex_document(document_id: int, current_user: UserPublic = Depends(get_current_user)) -> DocumentSummary:
    return index_management_service.reindex_document(document_id, current_user.id)


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, current_user: UserPublic = Depends(get_current_user)) -> dict[str, str]:
    return index_management_service.delete_document(document_id, current_user.id)


@router.post("/workspaces/{workspace_id}/index/rebuild", response_model=IndexStatusResponse)
def rebuild_workspace_index(workspace_id: int, current_user: UserPublic = Depends(get_current_user)) -> IndexStatusResponse:
    return index_management_service.rebuild_workspace(workspace_id, current_user.id)


@router.get("/workspaces/{workspace_id}/index/logs", response_model=list[IndexLogEntry])
def index_logs(workspace_id: int, current_user: UserPublic = Depends(get_current_user)) -> list[IndexLogEntry]:
    return index_management_service.logs(workspace_id, current_user.id)


@router.get("/workspaces/{workspace_id}/index/status", response_model=IndexStatusResponse)
def index_status(workspace_id: int, current_user: UserPublic = Depends(get_current_user)) -> IndexStatusResponse:
    return index_management_service.status(workspace_id, current_user.id)
