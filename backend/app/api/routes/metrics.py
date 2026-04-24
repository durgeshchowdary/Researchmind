from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import SystemMetrics, UserPublic
from app.services.observability_service import observability_service


router = APIRouter()


@router.get("/system", response_model=SystemMetrics)
def system_metrics(_: UserPublic = Depends(get_current_user)) -> SystemMetrics:
    return observability_service.system_metrics()
