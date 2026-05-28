__all__ = ["EventHandler"]

from common.application.interfaces import IEventBus
from data_preparation.application.features import ingest_chat_export
from data_preparation.domain.entities import ChatExport


class EventHandler:
    def __init__(
            self,
            bus: IEventBus,
    ) -> None:
        self._bus = bus

    async def handle(
            self,
            event: ChatExport.EventChatExportCreated,
    ) -> None:
        await self._bus.group_apply([
            ingest_chat_export.Command(
                chat_export_id=ChatExport.ChatID(value=int(event.object_id)),
            ),
        ])
