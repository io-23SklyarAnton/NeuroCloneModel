__all__ = [
    "Command",
    "CommandHandler",
]

from typing import Optional

from domain.entities.bot import Bot
from domain.entities.user import User
from domain.value_objects import ID
from features import interfaces
from features.base import ICommand, Response


class Command(ICommand):
    bot_id: ID
    requester_telegram_id: User.TelegramID


class CommandHandler:
    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
            bot_runner: interfaces.IBotRunnerService,
    ) -> None:
        self._uow = uow
        self._bot_runner = bot_runner

    async def handle(
            self,
            command: Command,
    ) -> Response:
        requester: Optional[User] = await self._uow.user.get_by_id_optional(command.requester_telegram_id)
        if requester is None:
            return Response(message="You need to register first by sending /start.")

        bot: Optional[Bot] = await self._uow.bot.get_by_id_optional(command.bot_id)
        if bot is None:
            return Response(message="Bot not found.")

        try:
            bot.ensure_owned_by(requester.id)
        except Bot.NotOwnedError:
            return Response(message="You don't own this bot.")

        try:
            bot.start_bot()
        except Bot.IllegalStateTransitionError:
            return Response(message=f"Bot «{bot.name.value}» is already running.")

        await self._bot_runner.start(
            bot_id=bot.id,
            token=bot.token,
        )

        self._uow.bot.update(bot)
        self._uow.commit()

        return Response(message=f"Bot «{bot.name.value}» is now {bot.status.value}.")
