__all__ = ["InMemoryParsedMessageRepository"]

from typing import Optional

from common.domain.value_objects import ID
from common.infrastructure.db.in_memory_repository import InMemoryBaseRepository
from ml_pipeline.application.interfaces.repositories import IParsedMessageRepository
from ml_pipeline.domain.entities import ChatExport, ParsedMessage


class InMemoryParsedMessageRepository(InMemoryBaseRepository[ParsedMessage], IParsedMessageRepository):
    def __init__(
            self,
            storage: dict[ID, ParsedMessage],
    ):
        super().__init__(storage)

    def create_many(
            self,
            messages: list[ParsedMessage],
    ) -> None:
        for message in messages:
            self.create(message)

    async def get_by_id_optional(
            self,
            message_id: ID,
    ) -> Optional[ParsedMessage]:
        return self.get_optional(message_id)

    async def get_batch_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
            offset: int,
            limit: int,
    ) -> list[ParsedMessage]:
        chat_messages: list[ParsedMessage] = [
            message for message in self._storage.values()
            if message.chat_export_id == chat_export_id
        ]
        chat_messages.sort(key=lambda m: m.sequence_number.value)

        return chat_messages[offset:offset + limit]

    async def get_by_thread_id(
            self,
            thread_id: ID,
    ) -> list[ParsedMessage]:
        thread_messages: list[ParsedMessage] = [
            message for message in self._storage.values()
            if message.thread_id == thread_id
        ]
        thread_messages.sort(key=lambda m: m.sequence_number.value)

        return thread_messages

    async def get_by_chat_and_external_id_optional(
            self,
            chat_export_id: ChatExport.ChatID,
            external_id: ParsedMessage.ExternalID,
    ) -> Optional[ParsedMessage]:
        for message in self._storage.values():
            if message.chat_export_id == chat_export_id and message.external_id == external_id:
                return message

        return None

    async def count_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> int:
        return sum(
            1 for message in self._storage.values()
            if message.chat_export_id == chat_export_id
        )
