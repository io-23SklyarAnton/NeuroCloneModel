__all__ = ["EventHandler"]

from common.application.interfaces import IEventBus
from data_preparation.application.features import build_imitation_dataset
from data_preparation.domain.entities import ChatExport


class EventHandler:
    def __init__(
            self,
            bus: IEventBus,
    ) -> None:
        self._bus = bus

    async def handle(
            self,
            event: ChatExport.EventChatExportReady,
    ) -> None:
        await self._bus.group_apply([
            build_imitation_dataset.Command(
                chat_export_id=ChatExport.ChatID(value=int(event.object_id)),
            ),
        ])
