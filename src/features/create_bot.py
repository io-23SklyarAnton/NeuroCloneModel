__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

from typing import Optional

from domain.entities import User
from domain.entities.bot import Bot
from features import interfaces
from features.base import ICommand, Response


class Command(ICommand):
    requester_telegram_id: User.TelegramID
    bot_name: Bot.Name
    bot_token: Bot.Token


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

        bot: Optional[Bot] = await self._uow.bot.get_by_token_optional(command.bot_token)
        if bot is not None:
            return Response(message="Bot with this token already exists.")

        bot = Bot.create(
            name=command.bot_name,
            token=command.bot_token,
            owner_id=requester.id,
        )
        self._uow.bot.create(bot)

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
