from datetime import datetime, timezone

from app.db.session import get_db
from app.models.schemas import SystemMetrics


class ObservabilityService:
    def record_latency(self, name: str, latency_ms: float) -> None:
        self._increment(f"{name}_latency_total_ms", latency_ms)
        self._increment(f"{name}_latency_count", 1)

    def increment(self, name: str, amount: float = 1) -> None:
        self._increment(name, amount)

    def system_metrics(self) -> SystemMetrics:
        values = self._values()
        search_count = values.get("search_latency_count", 0)
        ask_count = values.get("ask_latency_count", 0)
        indexing_count = values.get("indexing_latency_count", 0)
        return SystemMetrics(
            search_latency_ms=self._average(values.get("search_latency_total_ms", 0), search_count),
            ask_latency_ms=self._average(values.get("ask_latency_total_ms", 0), ask_count),
            indexing_latency_ms=self._average(values.get("indexing_latency_total_ms", 0), indexing_count),
            failed_indexing_count=int(values.get("failed_indexing_count", 0)),
            total_documents_indexed=int(values.get("total_documents_indexed", 0)),
            total_chunks_indexed=int(values.get("total_chunks_indexed", 0)),
            warnings=[],
        )

    def _increment(self, name: str, amount: float) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO observability_metrics (name, value, count, updated_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(name) DO UPDATE SET
                    value = value + excluded.value,
                    count = count + 1,
                    updated_at = excluded.updated_at
                """,
                (name, float(amount), timestamp),
            )
            conn.commit()

    def _values(self) -> dict[str, float]:
        with get_db() as conn:
            rows = conn.execute("SELECT name, value FROM observability_metrics").fetchall()
        return {str(row["name"]): float(row["value"]) for row in rows}

    def _average(self, total: float, count: float) -> float:
        if count <= 0:
            return 0.0
        return round(total / count, 2)


observability_service = ObservabilityService()
