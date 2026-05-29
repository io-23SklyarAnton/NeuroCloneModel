__all__ = [
    "ingest_chat_export_task",
    "process_chat_threads_task",
    "build_imitation_dataset_task",
    "create_neuroclone_task",
    "train_lora_adapter_task",
    "assign_neuroclone_to_bot_task",
    "run_bot_task",
    "generate_persona_reply_task",
    "GeneratePersonaReplyPayload",
]

import uuid
from typing import Optional

import pydantic

from bot_operations.application.features import (
    assign_neuroclone_to_bot,
    run_bot,
)
from bot_operations.application.interfaces import ChatContextMessage
from data_preparation.application.features import (
    build_imitation_dataset,
    ingest_chat_export,
    process_chat_threads,
)
from infrastructure.celery import feature_dependencies as deps
from infrastructure.celery.utils import (
    catch_exceptions,
    run_async,
    set_request_id_from_task,
    task_with_custom_async,
    validate_payload,
)
from model_engine.application.features import (
    create_neuroclone,
    train_lora_adapter,
)


class GeneratePersonaReplyPayload(pydantic.BaseModel):
    neuroclone_id: uuid.UUID
    context: list[ChatContextMessage]


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(ingest_chat_export.Command)
def ingest_chat_export_task(
        payload: ingest_chat_export.Command,
) -> None:
    with deps.open_data_prep_uow() as uow:
        handler = deps.build_ingest_chat_export_handler(uow)
        run_async(handler.handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(process_chat_threads.Command)
def process_chat_threads_task(
        payload: process_chat_threads.Command,
) -> None:
    with deps.open_data_prep_uow() as uow:
        handler = deps.build_process_chat_threads_handler(uow)
        run_async(handler.handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(build_imitation_dataset.Command)
def build_imitation_dataset_task(
        payload: build_imitation_dataset.Command,
) -> None:
    with deps.open_data_prep_uow() as uow:
        handler = deps.build_build_imitation_dataset_handler(uow)
        run_async(handler.handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(create_neuroclone.Command)
def create_neuroclone_task(
        payload: create_neuroclone.Command,
) -> None:
    with deps.open_model_engine_uow() as uow:
        handler = deps.build_create_neuroclone_handler(uow)
        run_async(handler.handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(train_lora_adapter.Command)
def train_lora_adapter_task(
        payload: train_lora_adapter.Command,
) -> None:
    with deps.open_model_engine_uow() as uow:
        handler = deps.build_train_lora_adapter_handler(uow)
        run_async(handler.handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(assign_neuroclone_to_bot.Command)
def assign_neuroclone_to_bot_task(
        payload: assign_neuroclone_to_bot.Command,
) -> None:
    with deps.open_bot_ops_uow() as uow:
        handler = deps.build_assign_neuroclone_to_bot_handler(uow)
        run_async(handler.handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=True)
@set_request_id_from_task
@validate_payload(run_bot.Command)
def run_bot_task(
        payload: run_bot.Command,
) -> None:
    with deps.open_bot_ops_uow() as uow:
        handler = deps.build_run_bot_handler(uow)
        run_async(handler.handle(payload))


@task_with_custom_async(bind=True)
@catch_exceptions(is_critical=False)
@set_request_id_from_task
@validate_payload(GeneratePersonaReplyPayload)
def generate_persona_reply_task(
        payload: GeneratePersonaReplyPayload,
) -> Optional[str]:
    with deps.open_model_engine_uow() as uow:
        service = deps.build_persona_inference_service(uow)
        return run_async(service.generate_reply(
            neuroclone_id=payload.neuroclone_id,
            context=payload.context,
        ))
