__all__ = ["InMemoryThreadRepository"]

from typing import Optional

from common.domain.value_objects import ID
from common.infrastructure.in_memory_repository import InMemoryBaseRepository
from ml_pipeline.application.interfaces.repositories import IThreadRepository
from ml_pipeline.domain.entities import ChatExport, ParsedMessage, Thread
from ml_pipeline.infrastructure.in_memory.repositories.chat_export import InMemoryChatExportRepository


class InMemoryThreadRepository(InMemoryBaseRepository[Thread], IThreadRepository):
    def __init__(
            self,
            chat_export_repository: InMemoryChatExportRepository,
            storage: dict[ID, Thread],
    ):
        super().__init__(storage)
        self._chat_export_repository = chat_export_repository

    async def get_by_message_id(
            self,
            message_id: ID,
    ) -> Optional[Thread]:
        for chat_export in self._chat_export_repository.get_all():
            for message in chat_export.parsed_messages:
                if message.id == message_id and message.thread_id is not None:
                    return self.get_optional(message.thread_id)

        return None

    async def get_all_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> list[Thread]:
        return [
            thread for thread in self._storage.values()
            if thread.chat_export_id == chat_export_id
        ]

    async def get_messages_by_thread_id(
            self,
            thread_id: ID,
    ) -> list[ParsedMessage]:
        messages: list[ParsedMessage] = []
        for chat_export in self._chat_export_repository.get_all():
            for message in chat_export.parsed_messages:
                if message.thread_id == thread_id:
                    messages.append(message)

        messages.sort(key=lambda m: m.sequence_number.value)
        return messages
