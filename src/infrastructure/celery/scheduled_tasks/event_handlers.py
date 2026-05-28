__all__ = [
    "chat_export_created_task",
    "chat_export_ingested_task",
    "chat_export_ready_task",
    "dataset_built_task",
    "neuroclone_created_task",
    "neuroclone_ready_task",
    "neuroclone_assigned_task",
]

from bot_operations.application.features import (
    neuroclone_assigned,
    neuroclone_ready,
)
from bot_operations.domain.entities import Bot
from data_preparation.application.features import (
    chat_export_created,
    chat_export_ingested,
    chat_export_ready,
)
from data_preparation.domain.entities import ChatExport, TrainingDataset
from infrastructure.celery.utils import (
    catch_exceptions,
    run_async,
    set_request_id_from_task,
    task_with_custom_async,
    validate_payload,
)
from model_engine.application.features import (
    dataset_built,
    neuroclone_created,
)
from model_engine.domain.entities import NeuroClone


def _bus():
    from infrastructure.celery.event_bus import CeleryEventBus
    return CeleryEventBus()


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(ChatExport.EventChatExportCreated)
def chat_export_created_task(
        payload: ChatExport.EventChatExportCreated,
) -> None:
    run_async(chat_export_created.EventHandler(bus=_bus()).handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(ChatExport.EventChatExportIngested)
def chat_export_ingested_task(
        payload: ChatExport.EventChatExportIngested,
) -> None:
    run_async(chat_export_ingested.EventHandler(bus=_bus()).handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(ChatExport.EventChatExportReady)
def chat_export_ready_task(
        payload: ChatExport.EventChatExportReady,
) -> None:
    run_async(chat_export_ready.EventHandler(bus=_bus()).handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(TrainingDataset.EventDatasetBuilt)
def dataset_built_task(
        payload: TrainingDataset.EventDatasetBuilt,
) -> None:
    run_async(dataset_built.EventHandler(bus=_bus()).handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(NeuroClone.EventNeuroCloneCreated)
def neuroclone_created_task(
        payload: NeuroClone.EventNeuroCloneCreated,
) -> None:
    run_async(neuroclone_created.EventHandler(bus=_bus()).handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(NeuroClone.EventNeuroCloneReady)
def neuroclone_ready_task(
        payload: NeuroClone.EventNeuroCloneReady,
) -> None:
    run_async(neuroclone_ready.EventHandler(bus=_bus()).handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(Bot.NeuroCloneAssigned)
def neuroclone_assigned_task(
        payload: Bot.NeuroCloneAssigned,
) -> None:
    run_async(neuroclone_assigned.EventHandler(bus=_bus()).handle(payload))
