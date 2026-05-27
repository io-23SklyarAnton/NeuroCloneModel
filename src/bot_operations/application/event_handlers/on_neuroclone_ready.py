__all__ = [
    "OnNeuroCloneReadyHandler",
]

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from common.domain.value_objects import UserName, OwnerTelegramID
from contracts.integration_events import NeuroCloneReadyEvent


class OnNeuroCloneReadyHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def handle(
            self,
            event: NeuroCloneReadyEvent,
    ) -> None:
        affected_bots: list[Bot] = await self._uow.bot.get_by_owner_and_target_user(
            owner_id=OwnerTelegramID(value=event.owner_telegram_id),
            target_user_name=UserName(value=event.target_user_name),
        )
        if not affected_bots:
            return

        for bot in affected_bots:
            bot.bind_neuroclone(Bot.NeuroCloneID(value=event.neuroclone_id))
            self._uow.bot.update(bot)

        await self._uow.commit()
