__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

from typing import Optional

from bot_operations.application import constants
from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from common.application.base import ICommand, Response
from common.domain.value_objects import UserName


class Command(ICommand):
    owner_id: Bot.OwnerTelegramID
    bot_name: Bot.Name
    bot_token: Bot.Token
    target_user_name: UserName


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
        existing_bot: Optional[Bot] = await self._uow.bot.get_by_token_optional(command.bot_token)
        if existing_bot is not None:
            return Response(message="Bot with this token already exists.")

        owner_bots: list[Bot] = await self._uow.bot.get_by_owner_id(command.owner_id)
        if len(owner_bots) >= constants.USER_BOT_LIMIT:
            return Response(
                message=f"You have reached the maximum number of bots ({constants.USER_BOT_LIMIT}).",
            )

        bot: Bot = Bot.create(
            owner_id=command.owner_id,
            token=command.bot_token,
            name=command.bot_name,
            target_user_name=command.target_user_name,
        )
        self._uow.bot.create(bot)
        await self._uow.commit()

        return Response(
            message=(
                f"Bot «{bot.name.value}» registered as {bot.status.value}. "
                f"Neuroclone for «{command.target_user_name.value}» will be bound once training completes."
            ),
        )
