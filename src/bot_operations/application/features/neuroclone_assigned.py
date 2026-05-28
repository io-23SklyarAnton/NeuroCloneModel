__all__ = ["EventHandler"]

import uuid

from bot_operations.application.features import run_bot
from bot_operations.domain.entities import Bot
from common.application.interfaces import IEventBus
from common.domain.value_objects import ID


class EventHandler:
    def __init__(
            self,
            bus: IEventBus,
    ) -> None:
        self._bus = bus

    async def handle(
            self,
            event: Bot.NeuroCloneAssigned,
    ) -> None:
        await self._bus.group_apply([
            run_bot.Command(
                bot_id=ID(value=uuid.UUID(event.object_id)),
            ),
        ])
