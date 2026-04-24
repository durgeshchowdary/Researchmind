from app.db.session import get_db
from app.models.schemas import AdminObservabilityResponse, SystemMetrics
from app.services.document_service import document_service
from app.services.observability_service import observability_service
from app.services.task_service import task_service
from app.services.workspace_service import workspace_service


class AdminObservabilityService:
    def admin(self) -> AdminObservabilityResponse:
        metrics = observability_service.system_metrics()
        stats = document_service.get_stats(None)
        with get_db() as conn:
            eval_runs = conn.execute("SELECT COUNT(*) AS count FROM eval_runs").fetchone()
            task_failures = conn.execute("SELECT COUNT(*) AS count FROM indexing_tasks WHERE status = 'failed'").fetchone()
        return AdminObservabilityResponse(
            **metrics.model_dump(),
            queue_mode=task_service.indexing_mode(),
            redis_available=task_service.redis_available(),
            document_count=stats.document_count,
            chunk_count=stats.chunk_count,
            evaluation_runs=int(eval_runs["count"] or 0),
            task_failure_count=int(task_failures["count"] or 0),
        )

    def workspace_metrics(self, workspace_id: int, user_id: int) -> SystemMetrics:
        workspace_service.require_role(user_id, workspace_id, "viewer")
        metrics = observability_service.system_metrics()
        stats = document_service.get_stats(user_id, workspace_id)
        metrics.warnings = [f"Workspace has {stats.document_count} document(s) and {stats.chunk_count} chunk(s)."]
        return metrics


admin_observability_service = AdminObservabilityService()
