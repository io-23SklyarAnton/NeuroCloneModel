__all__ = ["dispatch_events"]

from sqlalchemy.orm import Session

from bot_operations.domain.entities import Bot
from common.domain.entities import Aggregate
from common.infrastructure.db.models import OutboxMessage
from common.infrastructure.db.utils import get_db, get_utc_now_naive
from data_preparation.domain.entities import ChatExport, TrainingDataset
from infrastructure.celery.scheduled_tasks import event_handlers
from infrastructure.celery.utils import (
    catch_exceptions,
    set_request_id_from_task,
    task_with_custom_async,
)
from infrastructure.outbox_worker.queries import get_unscheduled_outbox_messages
from model_engine.domain.entities import NeuroClone


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
def dispatch_events() -> None:
    session: Session = get_db()
    now = get_utc_now_naive()

    try:
        for outbox_message in get_unscheduled_outbox_messages(session):
            _route(outbox_message)
            outbox_message.scheduled_at = now

        session.commit()
    finally:
        session.close()


def _route(outbox_message: OutboxMessage) -> None:
    match outbox_message.name:
        case ChatExport.EventChatExportCreated.__name__:
            event_handlers.chat_export_created_task.apply_async(
                kwargs=_to_payload(outbox_message, ChatExport.EventChatExportCreated),
            )
        case ChatExport.EventChatExportIngested.__name__:
            event_handlers.chat_export_ingested_task.apply_async(
                kwargs=_to_payload(outbox_message, ChatExport.EventChatExportIngested),
            )
        case ChatExport.EventChatExportReady.__name__:
            event_handlers.chat_export_ready_task.apply_async(
                kwargs=_to_payload(outbox_message, ChatExport.EventChatExportReady),
            )
        case TrainingDataset.EventDatasetBuilt.__name__:
            event_handlers.dataset_built_task.apply_async(
                kwargs=_to_payload(outbox_message, TrainingDataset.EventDatasetBuilt),
            )
        case NeuroClone.EventNeuroCloneCreated.__name__:
            event_handlers.neuroclone_created_task.apply_async(
                kwargs=_to_payload(outbox_message, NeuroClone.EventNeuroCloneCreated),
            )
        case NeuroClone.EventNeuroCloneReady.__name__:
            event_handlers.neuroclone_ready_task.apply_async(
                kwargs=_to_payload(outbox_message, NeuroClone.EventNeuroCloneReady),
            )
        case Bot.NeuroCloneAssigned.__name__:
            event_handlers.neuroclone_assigned_task.apply_async(
                kwargs=_to_payload(outbox_message, Bot.NeuroCloneAssigned),
            )


def _to_payload(
        outbox_message: OutboxMessage,
        event_class: type[Aggregate.IDomainEvent],
) -> dict:
    event = event_class(
        id=outbox_message.id,
        object_id=outbox_message.object_id,
        payload=event_class.Payload.model_validate(outbox_message.data),
    )
    return dict(payload=event.model_dump(mode="json"))
