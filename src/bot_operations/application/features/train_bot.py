__all__ = [
    "Command",
    "CommandHandler",
]

from pathlib import Path

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from common.application.base import ICommand, Response
from common.domain.value_objects import ID
from ml_pipeline.application.interfaces import IInferenceEngine


class Command(ICommand):
    bot_id: ID
    train_data_path: Path
    adapter_path: Path


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            inference_engine: IInferenceEngine,
    ) -> None:
        self._uow = uow
        self._inference_engine = inference_engine

    async def handle(
            self,
            command: Command,
    ) -> Response:
        bot: Bot = await self._uow.bot.get_by_id_or_raise(command.bot_id)

        await self._inference_engine.train_lora(
            train_data_path=str(command.train_data_path),
            adapter_path=str(command.adapter_path),
        )

        bot.attach_lora(Bot.LoraPath(value=str(command.adapter_path)))
        self._uow.bot.update(bot)
        await self._uow.commit()

        return Response(
            message=f"Bot «{bot.name.value}» trained successfully; lora attached at {bot.lora_path.value}.",
        )
