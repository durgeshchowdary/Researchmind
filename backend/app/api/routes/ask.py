from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import AskRequest, AskResponse
from app.models.schemas import UserPublic
from app.services.rag_service import rag_service


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest, current_user: UserPublic = Depends(get_current_user)) -> AskResponse:
    return await rag_service.answer_question(payload, current_user.id)
