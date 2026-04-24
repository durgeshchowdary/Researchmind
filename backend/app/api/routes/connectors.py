from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import ConnectorImportResponse, UserPublic, WebUrlImportRequest
from app.services.connector_service import connector_service


router = APIRouter()


@router.post("/web-url/import", response_model=ConnectorImportResponse)
def import_web_url(payload: WebUrlImportRequest, current_user: UserPublic = Depends(get_current_user)) -> ConnectorImportResponse:
    return connector_service.import_web_url(payload, current_user.id)
