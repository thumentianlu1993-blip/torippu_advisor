from celery import Celery

from app.config import settings

celery_app = Celery(
    "travel_planner",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.collection",
        "app.tasks.report",
        "app.tasks.outbox",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=1800,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "dispatch-task-outbox": {
            "task": "app.tasks.outbox.dispatch_task_outbox",
            "schedule": 5.0,
        },
        "purge-expired-projects": {
            "task": "app.tasks.maintenance.purge_expired_projects",
            "schedule": 3600.0,
        },
        "recover-stale-collection-runs": {
            "task": "app.tasks.maintenance.recover_stale_collection_runs",
            "schedule": 30.0,
        },
    },
)
