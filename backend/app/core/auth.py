from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.schemas import UserPublic
from app.services.auth_service import auth_service


bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> UserPublic:
    return auth_service.get_user_by_token(credentials.credentials)
