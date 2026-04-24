from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.session import get_db
from app.models.schemas import DocumentSummary, IndexLogEntry, IndexStatusResponse
from app.services.document_service import document_service
from app.services.indexing_service import indexing_service
from app.services.task_service import task_service
from app.services.workspace_service import workspace_service


class IndexManagementService:
    def reindex_document(self, document_id: int, user_id: int) -> DocumentSummary:
        document = document_service.get_document_detail(document_id, user_id)
        if not document or document.workspace_id is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        workspace_service.require_role(user_id, document.workspace_id, "editor")
        document_service.process_document(document_id)
        indexing_service.rebuild_indexes()
        self.log(document.workspace_id, document_id, "info", "Document reindexed.")
        refreshed = document_service.get_document_detail(document_id, user_id, document.workspace_id)
        return DocumentSummary(**refreshed.model_dump(exclude={"chunks"}))

    def delete_document(self, document_id: int, user_id: int) -> dict[str, str]:
        document = document_service.get_document_detail(document_id, user_id)
        if not document or document.workspace_id is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        workspace_service.require_role(user_id, document.workspace_id, "owner")
        with get_db() as conn:
            conn.execute("DELETE FROM documents WHERE id = ? AND workspace_id = ?", (document_id, document.workspace_id))
            conn.commit()
        indexing_service.rebuild_indexes()
        self.log(document.workspace_id, document_id, "info", "Document deleted and indexes rebuilt.")
        return {"status": "deleted"}

    def rebuild_workspace(self, workspace_id: int, user_id: int) -> IndexStatusResponse:
        workspace_service.require_role(user_id, workspace_id, "owner")
        indexing_service.rebuild_indexes()
        self.log(workspace_id, None, "info", "Workspace index rebuild requested.")
        return self.status(workspace_id, user_id)

    def status(self, workspace_id: int, user_id: int) -> IndexStatusResponse:
        workspace_service.require_role(user_id, workspace_id, "viewer")
        stats = document_service.get_stats(user_id, workspace_id)
        with get_db() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM indexing_tasks WHERE workspace_id = ? AND status = 'failed'",
                (workspace_id,),
            ).fetchone()
        warnings = []
        if not task_service.redis_available():
            warnings.append("Redis is unavailable; background or synchronous indexing fallback is active.")
        return IndexStatusResponse(
            workspace_id=workspace_id,
            document_count=stats.document_count,
            indexed_document_count=stats.indexed_document_count,
            chunk_count=stats.chunk_count,
            failed_tasks=int(row["count"] or 0),
            queue_mode=task_service.indexing_mode(),
            redis_available=task_service.redis_available(),
            warnings=warnings,
        )

    def logs(self, workspace_id: int, user_id: int) -> list[IndexLogEntry]:
        workspace_service.require_role(user_id, workspace_id, "viewer")
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM index_logs WHERE workspace_id = ? ORDER BY datetime(created_at) DESC LIMIT 100",
                (workspace_id,),
            ).fetchall()
        return [
            IndexLogEntry(
                id=int(row["id"]),
                workspace_id=int(row["workspace_id"]),
                document_id=int(row["document_id"]) if row["document_id"] is not None else None,
                level=str(row["level"]),
                message=str(row["message"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
            for row in rows
        ]

    def log(self, workspace_id: int, document_id: int | None, level: str, message: str) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO index_logs (workspace_id, document_id, level, message, created_at) VALUES (?, ?, ?, ?, ?)",
                (workspace_id, document_id, level, message, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()


index_management_service = IndexManagementService()
