__all__ = [
    "Command",
    "CommandHandler",
    "Response",
    "BotView",
]

import uuid
from typing import Optional

import pydantic

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from common.application.base import ICommand
from common.domain.value_objects import OwnerTelegramID


class Command(ICommand):
    owner_id: OwnerTelegramID


class BotView(pydantic.BaseModel):
    name: str
    status: Bot.BotStatus


class Response(pydantic.BaseModel):
    bots: list[BotView]


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
        bots: list[Bot] = await self._uow.bot.get_by_owner_id(command.owner_id)

        return Response(
            bots=[self._to_view(bot) for bot in bots],
        )

    @staticmethod
    def _to_view(
            bot: Bot,
    ) -> BotView:
        return BotView(
            name=bot.name.value,
            status=bot.status,
        )
