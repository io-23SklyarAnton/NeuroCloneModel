__all__ = ["celery_app"]

import logging
from datetime import timedelta

from celery import Celery
from celery.signals import setup_logging

import config


@setup_logging.connect
def _configure_logging(**_: object) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


celery_app: Celery = Celery(
    "worker",
    broker=config.RABBITMQ_LINK,
    backend=config.REDIS_LINK,
)
celery_app.autodiscover_tasks(packages=[
    "infrastructure.celery.periodic_tasks",
    "infrastructure.celery.scheduled_tasks",
])

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_scheduler="celery.beat.PersistentScheduler",
    broker_heartbeat=0,
    broker_connection_retry_on_startup=True,
)

celery_app.conf.task_routes = {
    "process_chat_threads_task": {"queue": "ml"},
    "train_lora_adapter_task": {"queue": "ml"},
}

celery_app.conf.beat_schedule = {
    "dispatch_events": {
        "task": "dispatch_events",
        "schedule": timedelta(seconds=5),
    },
}
