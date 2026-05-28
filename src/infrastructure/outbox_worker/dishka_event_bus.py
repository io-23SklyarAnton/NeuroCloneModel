__all__ = ["DishkaEventBus"]

import asyncio

from dishka import AsyncContainer

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
from model_engine.application.features import (
    create_neuroclone,
    train_lora_adapter,
)


_COMMAND_TO_HANDLER: dict[type[ICommand], type] = {
    ingest_chat_export.Command: ingest_chat_export.CommandHandler,
    process_chat_threads.Command: process_chat_threads.CommandHandler,
    build_imitation_dataset.Command: build_imitation_dataset.CommandHandler,
    create_neuroclone.Command: create_neuroclone.CommandHandler,
    train_lora_adapter.Command: train_lora_adapter.CommandHandler,
    assign_neuroclone_to_bot.Command: assign_neuroclone_to_bot.CommandHandler,
    run_bot.Command: run_bot.CommandHandler,
}


class DishkaEventBus(IEventBus):
    def __init__(
            self,
            container: AsyncContainer,
    ) -> None:
        self._container = container

    async def group_apply(
            self,
            commands: list[ICommand],
    ) -> None:
        await asyncio.gather(*[
            self._dispatch(command)
            for command in commands
        ])

    async def _dispatch(
            self,
            command: ICommand,
    ) -> None:
        handler_type: type = _COMMAND_TO_HANDLER[type(command)]
        async with self._container() as request_container:
            handler = await request_container.get(handler_type)
            await handler.handle(command)
