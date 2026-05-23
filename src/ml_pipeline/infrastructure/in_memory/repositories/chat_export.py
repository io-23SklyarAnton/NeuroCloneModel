__all__ = ["InMemoryChatExportRepository"]

from typing import Optional

from common.infrastructure.in_memory_repository import InMemoryBaseRepository
from ml_pipeline.application.interfaces.repositories import IChatExportRepository
from ml_pipeline.domain.entities import ChatExport, ParsedMessage


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

    async def get_messages_batch(
            self,
            chat_id: ChatExport.ChatID,
            offset: int,
            limit: int,
    ) -> list[ParsedMessage]:
        chat_export: Optional[ChatExport] = self.get_optional(chat_id)
        if chat_export is None:
            return []

        messages = sorted(
            chat_export.parsed_messages,
            key=lambda m: m.sequence_number.value,
        )
        return messages[offset:offset + limit]
