from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import AdminObservabilityResponse, SystemMetrics, UserPublic
from app.services.admin_observability_service import admin_observability_service


router = APIRouter()


@router.get("/admin/observability", response_model=AdminObservabilityResponse)
def admin_observability(_: UserPublic = Depends(get_current_user)) -> AdminObservabilityResponse:
    return admin_observability_service.admin()


@router.get("/workspaces/{workspace_id}/metrics", response_model=SystemMetrics)
def workspace_metrics(workspace_id: int, current_user: UserPublic = Depends(get_current_user)) -> SystemMetrics:
    return admin_observability_service.workspace_metrics(workspace_id, current_user.id)
