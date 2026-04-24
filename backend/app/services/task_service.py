import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, UploadFile

from app.core.config import get_settings
from app.core.exceptions import DuplicateDocumentError, ResearchMindError
from app.db.session import get_db
from app.models.schemas import DocumentSummary, TaskSummary
from app.services.document_service import document_service
from app.services.indexing_service import indexing_service
from app.services.observability_service import observability_service
from app.services.workspace_service import workspace_service


logger = logging.getLogger(__name__)
settings = get_settings()


class TaskService:
    async def enqueue_uploads(
        self,
        files: list[UploadFile],
        user_id: int,
        background_tasks: BackgroundTasks | None = None,
        workspace_id: int | None = None,
    ) -> tuple[list[DocumentSummary], int, list[str], list[str], str, list[str]]:
        documents: list[DocumentSummary] = []
        task_ids: list[str] = []
        failures: list[str] = []
        duplicates = 0
        warnings: list[str] = []
        mode = self.indexing_mode()
        resolved_workspace_id = workspace_service.resolve_workspace_id(user_id, workspace_id)
        workspace_service.require_role(user_id, resolved_workspace_id, "editor")

        for upload in files:
            file_name = upload.filename or "untitled"
            file_ext = Path(file_name).suffix.lower()
            if file_ext not in {".pdf", ".txt", ".md"}:
                failures.append(f"{file_name}: unsupported file type")
                continue
            content = await upload.read()
            if not content or not content.strip():
                failures.append(f"{file_name}: file is empty")
                continue
            checksum = f"{resolved_workspace_id}_{hashlib.sha256(content).hexdigest()}"
            task_id = f"idx_{uuid.uuid4().hex}"
            try:
                document = document_service.save_uploaded_document(
                    file_name,
                    file_ext,
                    checksum,
                    content,
                    user_id,
                    task_id,
                    workspace_id=resolved_workspace_id,
                )
                self.create_task(task_id, document.id, "queued", 10, mode, resolved_workspace_id)
                documents.append(document)
                task_ids.append(task_id)
                if mode == "celery":
                    try:
                        from app.worker.tasks import index_document_task

                        index_document_task.delay(document.id, task_id)
                    except Exception as exc:
                        warnings.append(f"Celery queue failed for {file_name}; falling back to local background task.")
                        logger.warning("Celery enqueue failed: %s", exc)
                        if background_tasks:
                            background_tasks.add_task(self.run_task, document.id, task_id, "background")
                        else:
                            self.run_task(document.id, task_id, "synchronous")
                            documents[-1] = self._document_snapshot(document.id)
                elif mode == "background" and background_tasks:
                    background_tasks.add_task(self.run_task, document.id, task_id, mode)
                else:
                    self.run_task(document.id, task_id, "synchronous")
                    documents[-1] = self._document_snapshot(document.id)
            except DuplicateDocumentError:
                duplicates += 1
            except ResearchMindError as exc:
                failures.append(f"{file_name}: {exc.message}")
            except Exception as exc:
                logger.exception("Unexpected upload queue failure for %s", file_name)
                failures.append(f"{file_name}: unexpected upload error")
        if mode != "celery":
            warnings.append(f"Indexing mode: {mode}. Redis/Celery is optional and the app remains usable without it.")
        return documents, duplicates, failures, task_ids, mode, warnings

    def run_task(self, document_id: int, task_id: str, mode: str | None = None) -> None:
        try:
            self.update_task(task_id, "processing", 25)
            with get_db() as conn:
                conn.execute(
                    "UPDATE documents SET status = 'processing', status_message = ?, progress = ? WHERE id = ?",
                    ("Processing document.", 25, document_id),
                )
                conn.commit()
            document_service.process_document(document_id)
            self.update_task(task_id, "chunked", 75)
            indexing_service.rebuild_indexes()
            self.update_task(task_id, "indexed", 100, completed=True)
        except Exception as exc:
            logger.exception("Indexing task failed for document %s", document_id)
            message = str(exc) or "Indexing failed"
            self.update_task(task_id, "failed", 100, message, completed=True)
            observability_service.increment("failed_indexing_count")
            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE documents
                    SET status = 'failed', status_message = ?, error_message = ?, progress = 100
                    WHERE id = ?
                    """,
                    (message, message, document_id),
                )
                conn.commit()

    def indexing_mode(self) -> str:
        if not settings.async_indexing_enabled:
            return "synchronous"
        if self.redis_available():
            return "celery"
        return "background"

    def redis_available(self) -> bool:
        try:
            import redis

            client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.4, socket_timeout=0.4)
            return bool(client.ping())
        except Exception:
            return False

    def create_task(
        self,
        task_id: str,
        document_id: int,
        status: str,
        progress: int,
        mode: str,
        workspace_id: int | None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO indexing_tasks (task_id, document_id, workspace_id, status, progress, created_at, updated_at, indexing_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, document_id, workspace_id, status, progress, timestamp, timestamp, mode),
            )
            conn.commit()

    def update_task(
        self,
        task_id: str,
        status: str,
        progress: int,
        error_message: str | None = None,
        completed: bool = False,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """
                UPDATE indexing_tasks
                SET status = ?, progress = ?, error_message = ?, updated_at = ?, completed_at = COALESCE(?, completed_at)
                WHERE task_id = ?
                """,
                (status, progress, error_message, timestamp, timestamp if completed else None, task_id),
            )
            conn.execute(
                "UPDATE documents SET task_id = ?, progress = ? WHERE task_id = ?",
                (task_id, progress, task_id),
            )
            conn.commit()

    def get_task(self, task_id: str, user_id: int | None = None) -> TaskSummary | None:
        with get_db() as conn:
            if user_id is None:
                row = conn.execute("SELECT * FROM indexing_tasks WHERE task_id = ?", (task_id,)).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT t.*
                    FROM indexing_tasks t
                    JOIN documents d ON d.id = t.document_id
                    WHERE t.task_id = ? AND d.user_id = ?
                    """,
                    (task_id, user_id),
                ).fetchone()
        return self._task_from_row(row) if row else None

    def list_tasks(self, user_id: int | None = None) -> list[TaskSummary]:
        with get_db() as conn:
            if user_id is None:
                rows = conn.execute("SELECT * FROM indexing_tasks ORDER BY datetime(created_at) DESC").fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT t.*
                    FROM indexing_tasks t
                    JOIN documents d ON d.id = t.document_id
                    WHERE d.user_id = ?
                    ORDER BY datetime(t.created_at) DESC
                    """,
                    (user_id,),
                ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def _task_from_row(self, row) -> TaskSummary:
        return TaskSummary(
            task_id=str(row["task_id"]),
            document_id=int(row["document_id"]),
            workspace_id=int(row["workspace_id"]) if "workspace_id" in row.keys() and row["workspace_id"] is not None else None,
            status=str(row["status"]),
            progress=int(row["progress"]),
            error_message=str(row["error_message"]) if row["error_message"] else None,
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            completed_at=datetime.fromisoformat(str(row["completed_at"])) if row["completed_at"] else None,
            indexing_mode=str(row["indexing_mode"]),
        )

    def _document_snapshot(self, document_id: int) -> DocumentSummary:
        document = document_service.get_document_detail(document_id)
        if not document:
            raise ResearchMindError("Document not found after indexing.", status_code=404)
        return DocumentSummary(**document.model_dump(exclude={"chunks"}))


task_service = TaskService()
