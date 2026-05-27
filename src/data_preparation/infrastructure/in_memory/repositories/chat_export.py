__all__ = ["InMemoryChatExportRepository"]

from typing import Optional

from common.infrastructure.db.in_memory_repository import InMemoryBaseRepository
from data_preparation.application.interfaces.repositories import IChatExportRepository
from data_preparation.domain.entities import ChatExport


class InMemoryChatExportRepository(InMemoryBaseRepository[ChatExport], IChatExportRepository):
    def __init__(
            self,
            storage: dict[ChatExport.ChatID, ChatExport],
    ):
        super().__init__(storage)

    async def get_by_id_or_raise(
            self,
            chat_id: ChatExport.ChatID,
    ) -> ChatExport:
        return self.get_or_raise(chat_id)

    async def get_by_id_optional(
            self,
            chat_id: ChatExport.ChatID,
    ) -> Optional[ChatExport]:
        return self.get_optional(chat_id)
