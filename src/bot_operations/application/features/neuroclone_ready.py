__all__ = ["EventHandler"]

import uuid

from bot_operations.application.features import assign_neuroclone_to_bot
from common.application.interfaces import IEventBus
from common.domain.value_objects import ID
from model_engine.domain.entities import NeuroClone


class EventHandler:
    def __init__(
            self,
            bus: IEventBus,
    ) -> None:
        self._bus = bus

    async def handle(
            self,
            event: NeuroClone.EventNeuroCloneReady,
    ) -> None:
        await self._bus.group_apply([
            assign_neuroclone_to_bot.Command(
                owner_id=event.payload.owner_telegram_id,
                neuroclone_id=ID(value=uuid.UUID(event.object_id)),
            ),
        ])
