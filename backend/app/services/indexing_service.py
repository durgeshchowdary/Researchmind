# FORCE REDEPLOY FIX
import json
import logging
import pickle
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    FAISS_AVAILABLE = False

from app.core.config import get_settings
from app.core.exceptions import EmbeddingUnavailableError
from app.db.session import get_db
from app.services.embedding_service import embedding_service
from app.services.observability_service import observability_service
from app.services.ranking_service import ranking_service
from app.utils.text import preprocess_text


logger = logging.getLogger(__name__)
settings = get_settings()

if not FAISS_AVAILABLE:
    logger.warning("FAISS not available. Semantic search will use fallback mode.")


class IndexingService:
    def __init__(self) -> None:
        self.inverted_index: dict[str, dict[int, int]] = {}
        self.doc_freqs: dict[str, int] = {}
        self.chunk_lengths: dict[int, int] = {}
        self.avg_chunk_length: float = 0.0
        self.chunk_title_matches: dict[int, float] = {}
        self.chunk_id_map: list[int] = []
        self.vector_index = None
        self.vector_available: bool = False

    @property
    def bm25_path(self) -> Path:
        return settings.index_path / "bm25.pkl"

    @property
    def faiss_path(self) -> Path:
        return settings.index_path / "chunks.faiss"

    @property
    def chunk_map_path(self) -> Path:
        return settings.index_path / "chunk_map.json"

    def load_persisted_state(self) -> None:
        settings.ensure_runtime_dirs()

        try:
            if self.bm25_path.exists():
                with self.bm25_path.open("rb") as file:
                    payload = pickle.load(file)
                    self.inverted_index = payload.get("inverted_index", {})
                    self.doc_freqs = payload.get("doc_freqs", {})
                    self.chunk_lengths = payload.get("chunk_lengths", {})
                    self.avg_chunk_length = payload.get("avg_chunk_length", 0.0)
                    self.chunk_title_matches = payload.get("chunk_title_matches", {})

            if not FAISS_AVAILABLE:
                logger.warning("Skipping FAISS index load because FAISS is not installed.")
                self.vector_index = None
                self.chunk_id_map = []
                self.vector_available = False
                return

            if self.faiss_path.exists() and self.chunk_map_path.exists():
                self.vector_index = faiss.read_index(str(self.faiss_path))
                self.chunk_id_map = json.loads(
                    self.chunk_map_path.read_text(encoding="utf-8")
                )
                self.vector_available = True
            else:
                logger.warning(
                    "FAISS index not found on startup. Semantic search will remain unavailable until indexing runs."
                )
                self.vector_index = None
                self.chunk_id_map = []
                self.vector_available = False

        except Exception:
            logger.exception(
                "Failed to load persisted indexes. Reverting to empty in-memory state."
            )
            self.inverted_index = {}
            self.doc_freqs = {}
            self.chunk_lengths = {}
            self.avg_chunk_length = 0.0
            self.chunk_title_matches = {}
            self.vector_index = None
            self.chunk_id_map = []
            self.vector_available = False

    def rebuild_indexes(self) -> None:
        started = time.perf_counter()
        logger.info("Rebuilding keyword and vector indexes")
        settings.ensure_runtime_dirs()

        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.text, d.title
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE d.status IN ('chunked', 'indexed')
                ORDER BY c.id
                """
            ).fetchall()

        inverted_index: dict[str, dict[int, int]] = defaultdict(dict)
        doc_freqs: Counter[str] = Counter()
        chunk_lengths: dict[int, int] = {}
        title_matches: dict[int, float] = {}
        texts: list[str] = []
        chunk_ids: list[int] = []

        for row in rows:
            chunk_id = int(row["id"])
            text = str(row["text"])
            title_terms = preprocess_text(str(row["title"]))
            terms = preprocess_text(text)
            frequencies = Counter(terms)

            chunk_lengths[chunk_id] = len(terms)
            texts.append(text)
            chunk_ids.append(chunk_id)
            title_matches[chunk_id] = float(len(set(terms) & set(title_terms)))

            for term, frequency in frequencies.items():
                inverted_index[term][chunk_id] = frequency
                doc_freqs[term] += 1

        self.inverted_index = dict(inverted_index)
        self.doc_freqs = dict(doc_freqs)
        self.chunk_lengths = chunk_lengths
        self.chunk_title_matches = title_matches
        self.avg_chunk_length = (
            sum(chunk_lengths.values()) / len(chunk_lengths) if chunk_lengths else 0.0
        )

        self._persist_bm25()
        self._rebuild_vector_index(chunk_ids, texts)
        self._mark_chunked_documents_as_indexed()

        observability_service.record_latency(
            "indexing", (time.perf_counter() - started) * 1000
        )
        observability_service.increment("total_chunks_indexed", len(chunk_ids))

    def _persist_bm25(self) -> None:
        payload = {
            "inverted_index": self.inverted_index,
            "doc_freqs": self.doc_freqs,
            "chunk_lengths": self.chunk_lengths,
            "avg_chunk_length": self.avg_chunk_length,
            "chunk_title_matches": self.chunk_title_matches,
        }

        with self.bm25_path.open("wb") as file:
            pickle.dump(payload, file)

    def _rebuild_vector_index(self, chunk_ids: list[int], texts: list[str]) -> None:
        if not texts:
            self.vector_index = None
            self.chunk_id_map = []
            self.vector_available = False

            if self.faiss_path.exists():
                self.faiss_path.unlink()
            if self.chunk_map_path.exists():
                self.chunk_map_path.unlink()
            return

        if not FAISS_AVAILABLE:
            logger.warning("Vector index rebuild skipped because FAISS is not installed.")
            self.vector_index = None
            self.chunk_id_map = []
            self.vector_available = False
            return

        try:
            vectors = embedding_service.encode(texts)
            dimension = vectors.shape[1]

            index = faiss.IndexFlatIP(dimension)
            index.add(vectors)

            self.vector_index = index
            self.chunk_id_map = chunk_ids
            self.vector_available = True

            faiss.write_index(index, str(self.faiss_path))
            self.chunk_map_path.write_text(json.dumps(chunk_ids), encoding="utf-8")

        except EmbeddingUnavailableError:
            logger.warning("Vector index rebuild skipped because embeddings are unavailable.")
            self.vector_index = None
            self.chunk_id_map = []
            self.vector_available = False

        except Exception:
            logger.exception("Vector index rebuild failed unexpectedly.")
            self.vector_index = None
            self.chunk_id_map = []
            self.vector_available = False

    def bm25_score(self, query_terms: list[str], limit: int) -> list[tuple[int, float]]:
        if not query_terms or not self.chunk_lengths:
            return []

        return ranking_service.bm25_score(
            query_terms,
            self.inverted_index,
            self.doc_freqs,
            self.chunk_lengths,
            self.avg_chunk_length,
            limit=limit,
            title_matches=self.chunk_title_matches,
            title_boost=settings.title_match_weight,
        )

    def semantic_score(self, query: str, limit: int) -> list[tuple[int, float]]:
        if not query or not self.vector_index or not self.chunk_id_map:
            return []

        try:
            vector = embedding_service.encode([query])
        except EmbeddingUnavailableError:
            return []

        search_limit = max(limit * settings.semantic_result_limit_multiplier, limit)
        scores, indices = self.vector_index.search(vector, search_limit)

        results: list[tuple[int, float]] = []
        for score, index in zip(scores[0], indices[0]):
            if index < 0 or index >= len(self.chunk_id_map):
                continue

            if float(score) < settings.semantic_min_score:
                continue

            results.append((self.chunk_id_map[index], float(score)))

            if len(results) >= limit:
                break

        return results

    def _mark_chunked_documents_as_indexed(self) -> None:
        status_message = "Indexed successfully"

        if not self.vector_available:
            status_message = "Keyword index ready; semantic index unavailable until embeddings load."

        with get_db() as conn:
            before = conn.execute(
                "SELECT COUNT(*) AS count FROM documents WHERE status IN ('chunked', 'indexed')"
            ).fetchone()

            now = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                UPDATE documents
                SET status = 'indexed',
                    status_message = ?,
                    last_indexed_at = ?,
                    indexed_at = ?,
                    progress = 100
                WHERE status IN ('chunked', 'indexed')
                """,
                (status_message, now, now),
            )

            conn.commit()

        observability_service.increment("total_documents_indexed", int(before["count"] or 0))

    def status_summary(self) -> dict[str, bool | str]:
        embedding_ready, embedding_status = embedding_service.status()

        return {
            "bm25_ready": bool(self.inverted_index),
            "vector_ready": self.vector_available,
            "embedding_model_ready": embedding_ready,
            "embedding_model_status": embedding_status,
            "faiss_available": FAISS_AVAILABLE,
            "faiss_path_exists": self.faiss_path.exists(),
        }


indexing_service = IndexingService()