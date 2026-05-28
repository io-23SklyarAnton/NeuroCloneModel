__all__ = ["CeleryEventBus"]

import celery

from bot_operations.application.features import (
    assign_neuroclone_to_bot,
    run_bot,
)
from common.application.base import ICommand
from common.application.interfaces import IEventBus
from data_preparation.application.features import (
    build_imitation_dataset,
    ingest_chat_export,
    process_chat_threads,
)
from infrastructure.celery.scheduled_tasks import command_handlers
from model_engine.application.features import (
    create_neuroclone,
    train_lora_adapter,
)


class CeleryEventBus(IEventBus):
    async def group_apply(self, commands: list[ICommand]) -> None:
        celery.group([
            self._signature_for(command)
            for command in commands
        ]).apply_async()

    def _signature_for(self, command: ICommand):
        payload = command.model_dump(mode="json")

        if isinstance(command, ingest_chat_export.Command):
            return command_handlers.ingest_chat_export_task.s(payload=payload)
        if isinstance(command, process_chat_threads.Command):
            return command_handlers.process_chat_threads_task.s(payload=payload)
        if isinstance(command, build_imitation_dataset.Command):
            return command_handlers.build_imitation_dataset_task.s(payload=payload)
        if isinstance(command, create_neuroclone.Command):
            return command_handlers.create_neuroclone_task.s(payload=payload)
        if isinstance(command, train_lora_adapter.Command):
            return command_handlers.train_lora_adapter_task.s(payload=payload)
        if isinstance(command, assign_neuroclone_to_bot.Command):
            return command_handlers.assign_neuroclone_to_bot_task.s(payload=payload)
        if isinstance(command, run_bot.Command):
            return command_handlers.run_bot_task.s(payload=payload)

        raise ValueError(f"Unknown command type: {type(command).__name__}")
