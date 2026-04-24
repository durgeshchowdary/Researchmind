from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.schemas import AuthResponse, LoginRequest, SignupRequest, UserPublic
from app.services.auth_service import auth_service


router = APIRouter()


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest) -> AuthResponse:
    return auth_service.signup(payload.name, payload.email, payload.password)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest) -> AuthResponse:
    return auth_service.login(payload.email, payload.password)


@router.get("/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user
