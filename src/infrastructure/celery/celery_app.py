__all__ = ["celery_app"]

from datetime import timedelta

from celery import Celery

import config

celery_app: Celery = Celery("worker", broker=config.RABBITMQ_LINK)
celery_app.autodiscover_tasks(packages=[
    "infrastructure.celery.periodic_tasks",
    "infrastructure.celery.scheduled_tasks",
])

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_scheduler="celery.beat.PersistentScheduler",
)

celery_app.conf.beat_schedule = {
    "dispatch_events": {
        "task": "dispatch_events",
        "schedule": timedelta(seconds=5),
    },
}
