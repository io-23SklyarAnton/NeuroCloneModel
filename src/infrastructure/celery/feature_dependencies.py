__all__ = [
    "build_storage",
    "build_inference_engine",
    "build_ingest_chat_export_handler",
    "build_process_chat_threads_handler",
    "build_build_imitation_dataset_handler",
    "build_create_neuroclone_handler",
    "build_train_lora_adapter_handler",
    "build_assign_neuroclone_to_bot_handler",
    "build_run_bot_handler",
    "open_data_prep_uow",
    "open_model_engine_uow",
    "open_bot_ops_uow",
]

from bot_operations.application.features import (
    assign_neuroclone_to_bot,
    run_bot,
)
from bot_operations.infrastructure.db import SqlAlchemyUnitOfWork as BotOpsUoW
from common.application.interfaces import IStorage
from common.infrastructure.db.utils import get_session_maker
from constants import BASE_PATH
from data_preparation.application.features import (
    build_imitation_dataset,
    ingest_chat_export,
    process_chat_threads,
)
from data_preparation.infrastructure.db import SqlAlchemyUnitOfWork as DataPrepUoW
from data_preparation.infrastructure.local.storage import LocalStorage
from infrastructure.llm import IInferenceEngine, MLXInferenceEngine
from model_engine.application.features import (
    create_neuroclone,
    train_lora_adapter,
)
from model_engine.infrastructure.db import SqlAlchemyUnitOfWork as ModelEngineUoW

_storage: IStorage | None = None
_inference_engine: IInferenceEngine | None = None


def build_storage() -> IStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage(base_path=BASE_PATH.parent / "storage")
    return _storage


def build_inference_engine() -> IInferenceEngine:
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = MLXInferenceEngine()
    return _inference_engine


def open_data_prep_uow() -> DataPrepUoW:
    return DataPrepUoW(session_factory=get_session_maker())


def open_model_engine_uow() -> ModelEngineUoW:
    return ModelEngineUoW(session_factory=get_session_maker())


def open_bot_ops_uow() -> BotOpsUoW:
    return BotOpsUoW(session_factory=get_session_maker())


def build_ingest_chat_export_handler(
        uow: DataPrepUoW,
) -> ingest_chat_export.CommandHandler:
    return ingest_chat_export.CommandHandler(
        uow=uow,
        storage=build_storage(),
    )


def build_process_chat_threads_handler(
        uow: DataPrepUoW,
) -> process_chat_threads.CommandHandler:
    return process_chat_threads.CommandHandler(
        uow=uow,
        inference_engine=build_inference_engine(),
    )


def build_build_imitation_dataset_handler(
        uow: DataPrepUoW,
) -> build_imitation_dataset.CommandHandler:
    return build_imitation_dataset.CommandHandler(
        uow=uow,
        storage=build_storage(),
    )


def build_create_neuroclone_handler(
        uow: ModelEngineUoW,
) -> create_neuroclone.CommandHandler:
    return create_neuroclone.CommandHandler(uow=uow)


def build_train_lora_adapter_handler(
        uow: ModelEngineUoW,
) -> train_lora_adapter.CommandHandler:
    return train_lora_adapter.CommandHandler(
        uow=uow,
        inference_engine=build_inference_engine(),
        storage=build_storage(),
    )


def build_assign_neuroclone_to_bot_handler(
        uow: BotOpsUoW,
) -> assign_neuroclone_to_bot.CommandHandler:
    return assign_neuroclone_to_bot.CommandHandler(uow=uow)


def build_run_bot_handler(
        uow: BotOpsUoW,
) -> run_bot.CommandHandler:
    return run_bot.CommandHandler(uow=uow)
