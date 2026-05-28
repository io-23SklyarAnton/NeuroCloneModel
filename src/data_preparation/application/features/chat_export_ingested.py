__all__ = ["EventHandler"]

from common.application.interfaces import IEventBus
from data_preparation.application.features import process_chat_threads
from data_preparation.domain.entities import ChatExport


class EventHandler:
    def __init__(
            self,
            bus: IEventBus,
    ) -> None:
        self._bus = bus

    async def handle(
            self,
            event: ChatExport.EventChatExportIngested,
    ) -> None:
        await self._bus.group_apply([
            process_chat_threads.Command(
                chat_export_id=ChatExport.ChatID(value=int(event.object_id)),
            ),
        ])
