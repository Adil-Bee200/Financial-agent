from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app instance
celery_app = Celery(
    "financial_agent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.celery_worker"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'fetch-articles-every-5-minutes': {
        'task': 'fetch_and_queue_articles',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'args': ('financial', 24),  # query='financial', hours_back=24
    },
}
