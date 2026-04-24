from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import RetrievalPlaygroundRequest, RetrievalPlaygroundResponse, UserPublic
from app.services.retrieval_playground_service import retrieval_playground_service


router = APIRouter()


@router.post("/playground", response_model=RetrievalPlaygroundResponse)
def retrieval_playground(
    payload: RetrievalPlaygroundRequest,
    current_user: UserPublic = Depends(get_current_user),
) -> RetrievalPlaygroundResponse:
    return retrieval_playground_service.run(payload, current_user.id)
