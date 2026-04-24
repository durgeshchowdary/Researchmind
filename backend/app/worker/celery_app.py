from app.core.config import get_settings


settings = get_settings()

try:
    from celery import Celery

    celery_app = Celery("researchmind", broker=settings.redis_url, backend=settings.redis_url)
    celery_app.conf.update(task_track_started=True, task_serializer="json", result_serializer="json")
except Exception:
    celery_app = None
