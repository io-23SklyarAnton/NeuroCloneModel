__all__ = ["dispatch_events"]

from sqlalchemy.orm import Session

from bot_operations.application.features import (
    neuroclone_assigned,
    neuroclone_ready,
)
from bot_operations.domain.entities import Bot
from common.application.interfaces import IEventBus
from common.domain.entities import Aggregate
from common.infrastructure.db.models import OutboxMessage
from common.infrastructure.db.utils import get_utc_now_naive
from data_preparation.application.features import (
    chat_export_created,
    chat_export_ingested,
    chat_export_ready,
)
from data_preparation.domain.entities import ChatExport, TrainingDataset
from infrastructure.outbox_worker.queries import get_unscheduled_outbox_messages
from model_engine.application.features import (
    dataset_built,
    neuroclone_created,
)
from model_engine.domain.entities import NeuroClone


async def dispatch_events(
        session: Session,
        bus: IEventBus,
) -> None:
    now = get_utc_now_naive()

    for outbox_message in get_unscheduled_outbox_messages(session):
        await _route(outbox_message, bus)
        outbox_message.scheduled_at = now

    session.commit()


async def _route(
        outbox_message: OutboxMessage,
        bus: IEventBus,
) -> None:
    match outbox_message.name:
        case ChatExport.EventChatExportCreated.__name__:
            await chat_export_created.EventHandler(bus=bus).handle(
                _to_event(outbox_message, ChatExport.EventChatExportCreated),
            )
        case ChatExport.EventChatExportIngested.__name__:
            await chat_export_ingested.EventHandler(bus=bus).handle(
                _to_event(outbox_message, ChatExport.EventChatExportIngested),
            )
        case ChatExport.EventChatExportReady.__name__:
            await chat_export_ready.EventHandler(bus=bus).handle(
                _to_event(outbox_message, ChatExport.EventChatExportReady),
            )
        case TrainingDataset.EventDatasetBuilt.__name__:
            await dataset_built.EventHandler(bus=bus).handle(
                _to_event(outbox_message, TrainingDataset.EventDatasetBuilt),
            )
        case NeuroClone.EventNeuroCloneCreated.__name__:
            await neuroclone_created.EventHandler(bus=bus).handle(
                _to_event(outbox_message, NeuroClone.EventNeuroCloneCreated),
            )
        case NeuroClone.EventNeuroCloneReady.__name__:
            await neuroclone_ready.EventHandler(bus=bus).handle(
                _to_event(outbox_message, NeuroClone.EventNeuroCloneReady),
            )
        case Bot.NeuroCloneAssigned.__name__:
            await neuroclone_assigned.EventHandler(bus=bus).handle(
                _to_event(outbox_message, Bot.NeuroCloneAssigned),
            )


def _to_event(
        outbox_message: OutboxMessage,
        event_class: type[Aggregate.IDomainEvent],
) -> Aggregate.IDomainEvent:
    return event_class(
        id=outbox_message.id,
        object_id=outbox_message.object_id,
        payload=event_class.Payload.model_validate(outbox_message.data),
    )
