__all__ = [
    "Command",
    "CommandHandler",
]

from typing import Optional

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from common.application.base import ICommand, Response
from common.domain.value_objects import ID


class Command(ICommand):
    bot_id: ID


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def handle(
            self,
            command: Command,
    ) -> Response:
        bot: Optional[Bot] = await self._uow.bot.get_by_id_optional(command.bot_id)
        if bot is None:
            return Response(message="Bot not found.")

        try:
            bot.start_bot()
        except Bot.NeuroCloneNotReadyError as exc:
            return Response(message=str(exc))
        except Bot.IllegalStateTransitionError:
            return Response(message=f"Bot «{bot.name.value}» is already running.")

        self._uow.bot.update(bot)
        await self._uow.commit()

        return Response(message=f"Bot «{bot.name.value}» marked as running.")
