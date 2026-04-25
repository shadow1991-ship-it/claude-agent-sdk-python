from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "sentinel_guard",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.scan_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=50,
    task_soft_time_limit=settings.SCAN_TIMEOUT_SECONDS,
    task_time_limit=settings.SCAN_TIMEOUT_SECONDS + 60,
)
