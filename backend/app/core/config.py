from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ResearchMind API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_origin: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cors_origin_regex: str | None = None
    database_path: str = "./data/researchmind.db"
    uploads_dir: str = "./data/uploads"
    index_dir: str = "./data/indexes"
    temp_dir: str = "./data/tmp"
    seed_dir: str = "./data/seed"
    chunk_size: int = 850
    chunk_overlap: int = 120
    top_k_default: int = 8
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    semantic_min_score: float = 0.2
    openai_base_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    hybrid_bm25_weight: float = 0.55
    hybrid_semantic_weight: float = 0.45
    title_match_weight: float = 0.25
    semantic_result_limit_multiplier: int = 3
    ask_min_grounded_score: float = 0.35
    ask_min_supported_terms: int = 1
    llm_timeout_seconds: int = 45
    jwt_secret: str = "dev-change-me-researchmind"
    jwt_expires_minutes: int = 60 * 24
    async_indexing_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    reranking_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    evaluation_dataset_path: str = "./data/eval/eval_dataset.json"

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if self.frontend_origin not in origins:
            origins.append(self.frontend_origin)
        return origins

    @property
    def database_file(self) -> Path:
        return Path(self.database_path).resolve()

    @property
    def uploads_path(self) -> Path:
        return Path(self.uploads_dir).resolve()

    @property
    def index_path(self) -> Path:
        return Path(self.index_dir).resolve()

    @property
    def seed_path(self) -> Path:
        return Path(self.seed_dir).resolve()

    @property
    def temp_path(self) -> Path:
        return Path(self.temp_dir).resolve()

    @property
    def evaluation_dataset_file(self) -> Path:
        return Path(self.evaluation_dataset_path).resolve()

    def ensure_runtime_dirs(self) -> None:
        self.database_file.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        self.seed_path.mkdir(parents=True, exist_ok=True)
        self.evaluation_dataset_file.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
