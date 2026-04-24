import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import ResearchMindError
from app.core.logging import configure_logging
from app.db.session import database_ready, initialize_database
from app.models.schemas import ApiErrorResponse, HealthDetailedResponse, HealthResponse
from app.services.embedding_service import embedding_service
from app.services.auth_service import auth_service
from app.services.indexing_service import indexing_service
from app.services.llm_client import llm_client
from app.services.workspace_service import workspace_service


settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    initialize_database()
    demo_user = auth_service.ensure_demo_user()
    workspace_service.ensure_default_workspace(demo_user)
    indexing_service.load_persisted_state()
    
    # Pre-load embedding model to avoid first-request latency
    logger.info("Pre-loading embedding model...")
    embedding_service.initialize() 
    
    embedding_ready, embedding_status = embedding_service.status()
    logger.info(
        "Startup check | env=%s | db_path=%s | db_ready=%s | uploads_path=%s | index_path=%s | temp_path=%s | embedding_model=%s | embedding_ready=%s | embedding_status=%s",
        settings.app_env,
        settings.database_file,
        database_ready(),
        settings.uploads_path,
        settings.index_path,
        settings.temp_path,
        settings.embedding_model,
        embedding_ready,
        embedding_status,
    )
    yield
    # Shutdown logic (clean up resources if needed)

app = FastAPI(
    title=settings.app_name, 
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(ResearchMindError)
async def researchmind_exception_handler(_: Request, exc: ResearchMindError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=ApiErrorResponse(detail=exc.message).model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return JSONResponse(
        status_code=500,
        content=ApiErrorResponse(detail="An unexpected backend error occurred. Please try again.").model_dump(),
    )


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    embedding_ready, _ = embedding_service.status()
    return HealthResponse(
        status="ok",
        database_ready=database_ready(),
        uploads_path=str(settings.uploads_path),
        index_path=str(settings.index_path),
        embedding_model=settings.embedding_model,
        embedding_model_ready=embedding_ready,
    )


@app.get("/health/detailed", response_model=HealthDetailedResponse)
def detailed_health_check() -> HealthDetailedResponse:
    index_status = indexing_service.status_summary()
    embedding_ready, embedding_status = embedding_service.status()
    return HealthDetailedResponse(
        status="ok",
        environment=settings.app_env,
        database_ready=database_ready(),
        database_path=str(settings.database_file),
        uploads_path=str(settings.uploads_path),
        index_path=str(settings.index_path),
        temp_path=str(settings.temp_path),
        embedding_model=settings.embedding_model,
        embedding_model_ready=embedding_ready,
        embedding_model_status=embedding_status,
        cors_origins=settings.allowed_cors_origins,
        cors_origin_regex=settings.cors_origin_regex,
        bm25_ready=bool(index_status["bm25_ready"]),
        faiss_index_present=bool(index_status["faiss_path_exists"]),
        semantic_search_ready=bool(index_status["vector_ready"]),
        llm_configured=llm_client.is_configured(),
    )
