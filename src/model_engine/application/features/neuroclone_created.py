__all__ = ["EventHandler"]

import uuid

from common.application.interfaces import IEventBus
from common.domain.value_objects import ID
from model_engine.application.features import train_lora_adapter
from model_engine.domain.entities import NeuroClone


class EventHandler:
    def __init__(
            self,
            bus: IEventBus,
    ) -> None:
        self._bus = bus

    async def handle(
            self,
            event: NeuroClone.EventNeuroCloneCreated,
    ) -> None:
        await self._bus.group_apply([
            train_lora_adapter.Command(
                neuroclone_id=ID(value=uuid.UUID(event.object_id)),
            ),
        ])
