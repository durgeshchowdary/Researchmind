from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import SearchRequest, SearchResponse
from app.models.schemas import UserPublic
from app.services.search_service import search_service


router = APIRouter()


@router.post("/keyword", response_model=SearchResponse)
def keyword_search(payload: SearchRequest, current_user: UserPublic = Depends(get_current_user)) -> SearchResponse:
    return search_service.keyword_search(payload, current_user.id)


@router.post("/semantic", response_model=SearchResponse)
def semantic_search(payload: SearchRequest, current_user: UserPublic = Depends(get_current_user)) -> SearchResponse:
    return search_service.semantic_search(payload, current_user.id)


@router.post("/hybrid", response_model=SearchResponse)
def hybrid_search(payload: SearchRequest, current_user: UserPublic = Depends(get_current_user)) -> SearchResponse:
    return search_service.hybrid_search(payload, current_user.id)
