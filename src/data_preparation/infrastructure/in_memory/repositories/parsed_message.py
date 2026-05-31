__all__ = ["InMemoryParsedMessageRepository"]

from typing import Optional

from common.domain.value_objects import ID, UserName
from common.infrastructure.db.in_memory_repository import InMemoryBaseRepository
from data_preparation.application.interfaces.repositories import IParsedMessageRepository
from data_preparation.domain.entities import ChatExport, ParsedMessage


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

    async def get_target_user_sequence_numbers_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
            target_user_name: UserName,
    ) -> list[int]:
        seq_numbers: list[int] = [
            message.sequence_number.value
            for message in self._storage.values()
            if message.chat_export_id == chat_export_id
            and message.from_user.value == target_user_name.value
        ]
        seq_numbers.sort()
        return seq_numbers

    async def get_recent_thread_ids_in_range(
            self,
            chat_export_id: ChatExport.ChatID,
            seq_start: int,
            seq_end: int,
            limit: int,
    ) -> list[ID]:
        last_seq_by_thread: dict[ID, int] = {}
        for message in self._storage.values():
            if message.chat_export_id != chat_export_id:
                continue
            if message.thread_id is None:
                continue
            seq: int = message.sequence_number.value
            if seq < seq_start or seq > seq_end:
                continue
            existing: Optional[int] = last_seq_by_thread.get(message.thread_id)
            if existing is None or seq > existing:
                last_seq_by_thread[message.thread_id] = seq

        ordered: list[tuple[ID, int]] = sorted(
            last_seq_by_thread.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return [thread_id for thread_id, _ in ordered[:limit]]

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
