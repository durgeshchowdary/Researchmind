import logging
from functools import cached_property

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.exceptions import EmbeddingUnavailableError


logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingService:
    def __init__(self) -> None:
        self._model_load_failed = False
        self._model_error_message: str | None = None

    def initialize(self) -> None:
        logger.info("Embedding model will load lazily on first semantic request.")

    @cached_property
    def model(self) -> SentenceTransformer:
        logger.info("Loading embedding model: %s", settings.embedding_model)
        try:
            return SentenceTransformer(settings.embedding_model)
        except Exception as exc:
            self._model_load_failed = True
            self._model_error_message = str(exc)
            logger.exception("Embedding model failed to load")
            raise EmbeddingUnavailableError(
                f"Embedding model '{settings.embedding_model}' could not be loaded.",
                status_code=503,
            ) from exc

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype="float32")
        vectors = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return vectors.astype("float32")

    def status(self) -> tuple[bool, str]:
        if "model" in self.__dict__:
            return True, "loaded"
        if self._model_load_failed:
            return False, self._model_error_message or "failed"
        return False, "not_loaded"


embedding_service = EmbeddingService()
