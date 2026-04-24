from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.models.schemas import CompareRequest, CompareResponse, UserPublic
from app.services.comparison_service import comparison_service


router = APIRouter()


@router.post("/compare", response_model=CompareResponse)
def compare_documents(payload: CompareRequest, current_user: UserPublic = Depends(get_current_user)) -> CompareResponse:
    try:
        return comparison_service.compare(payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
