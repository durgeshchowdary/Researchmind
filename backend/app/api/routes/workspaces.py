from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import (
    UserPublic,
    WorkspaceCreateRequest,
    WorkspaceDetail,
    WorkspaceMemberPatchRequest,
    WorkspaceMemberRequest,
    WorkspaceSummary,
)
from app.services.workspace_service import workspace_service


router = APIRouter()


@router.post("", response_model=WorkspaceSummary)
def create_workspace(payload: WorkspaceCreateRequest, current_user: UserPublic = Depends(get_current_user)) -> WorkspaceSummary:
    return workspace_service.create_workspace(payload, current_user)


@router.get("", response_model=list[WorkspaceSummary])
def list_workspaces(current_user: UserPublic = Depends(get_current_user)) -> list[WorkspaceSummary]:
    workspaces = workspace_service.list_workspaces(current_user.id)
    if not workspaces:
        return [workspace_service.ensure_default_workspace(current_user)]
    return workspaces


@router.get("/{workspace_id}", response_model=WorkspaceDetail)
def get_workspace(workspace_id: int, current_user: UserPublic = Depends(get_current_user)) -> WorkspaceDetail:
    return workspace_service.get_workspace(workspace_id, current_user.id)


@router.post("/{workspace_id}/members", response_model=WorkspaceDetail)
def add_member(
    workspace_id: int,
    payload: WorkspaceMemberRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> WorkspaceDetail:
    return workspace_service.add_member(workspace_id, current_user.id, payload.email, payload.role)


@router.patch("/{workspace_id}/members/{user_id}", response_model=WorkspaceDetail)
def patch_member(
    workspace_id: int,
    user_id: int,
    payload: WorkspaceMemberPatchRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> WorkspaceDetail:
    return workspace_service.patch_member(workspace_id, current_user.id, user_id, payload.role)


@router.delete("/{workspace_id}/members/{user_id}", response_model=WorkspaceDetail)
def delete_member(workspace_id: int, user_id: int, current_user: UserPublic = Depends(get_current_user)) -> WorkspaceDetail:
    return workspace_service.delete_member(workspace_id, current_user.id, user_id)
