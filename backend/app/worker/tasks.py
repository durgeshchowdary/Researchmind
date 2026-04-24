from app.services.task_service import task_service
from app.worker.celery_app import celery_app


if celery_app is not None:
    @celery_app.task(name="researchmind.index_document")
    def index_document_task(document_id: int, task_id: str) -> None:
        task_service.run_task(document_id, task_id, "celery")
else:
    class _FallbackTask:
        def delay(self, document_id: int, task_id: str) -> None:
            task_service.run_task(document_id, task_id, "synchronous")

    index_document_task = _FallbackTask()
