__all__ = [
    "Command",
    "CommandHandler",
]

from typing import Optional

from bot_operations.application.interfaces import (
    IBotRunnerService,
    IUnitOfWork,
    NeuroCloneReader,
)
from bot_operations.domain.entities import Bot
from common.application.base import ICommand, Response
from common.domain.value_objects import ID


class Command(ICommand):
    bot_id: ID


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            bot_runner: IBotRunnerService,
            neuroclone_reader: NeuroCloneReader,
    ) -> None:
        self._uow = uow
        self._bot_runner = bot_runner
        self._neuroclone_reader = neuroclone_reader

    async def handle(
            self,
            command: Command,
    ) -> Response:
        bot: Optional[Bot] = await self._uow.bot.get_by_id_optional(command.bot_id)
        if bot is None:
            return Response(message="Bot not found.")

        is_ready: bool = await self._neuroclone_reader.is_ready(bot.neuroclone_id.value)
        if not is_ready:
            return Response(
                message=(
                    f"Bot «{bot.name.value}» cannot start: "
                    f"neuroclone {bot.neuroclone_id.value} is not ready yet."
                ),
            )

        try:
            bot.start_bot()
        except Bot.IllegalStateTransitionError:
            return Response(message=f"Bot «{bot.name.value}» is already running.")

        await self._bot_runner.start(
            bot_id=bot.id,
            token=bot.token,
        )

        self._uow.bot.update(bot)
        await self._uow.commit()

        return Response(message=f"Bot «{bot.name.value}» started successfully.")
