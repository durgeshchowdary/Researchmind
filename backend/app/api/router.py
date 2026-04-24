from fastapi import APIRouter

from app.api.routes import (
    admin,
    api_platform,
    ask,
    auth,
    compare,
    connectors,
    documents,
    evaluation,
    index_management,
    metrics,
    retrieval,
    search,
    tasks,
    upload,
    workspaces,
)


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(ask.router, tags=["ask"])
api_router.include_router(compare.router, tags=["compare"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(retrieval.router, prefix="/retrieval", tags=["retrieval"])
api_router.include_router(connectors.router, prefix="/connectors", tags=["connectors"])
api_router.include_router(index_management.router, tags=["index-management"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(api_platform.router, tags=["api-platform"])
