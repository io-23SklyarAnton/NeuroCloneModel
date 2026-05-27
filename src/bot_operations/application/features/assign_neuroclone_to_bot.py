__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

from typing import Optional

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from common.application.base import ICommand, Response
from common.domain.value_objects import OwnerTelegramID, ID


class Command(ICommand):
    owner_id: OwnerTelegramID
    neuroclone_id: ID


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def handle(
            self,
            command: Command,
    ) -> None:
        bot: Optional[Bot] = await self._uow.bot.get_by_owner_id_without_neuroclone(command.owner_id)

        if bot is None:
            print(f"ERROR: No bot without neuroclone found for owner_id={command.owner_id.value}")
            return None

        bot.assign_neuroclone(command.neuroclone_id)
        self._uow.bot.update(bot)

        await self._uow.commit()

        return None
