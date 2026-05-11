from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.value_objects import ID
from features.interfaces.repositories.i_message import IMessageRepository
from infrastructure.in_memory.repositories.base import InMemoryBaseRepository


class InMemoryMessageRepository(InMemoryBaseRepository[Message], IMessageRepository):
    def __init__(
            self,
            storage: dict[ID, Message],
    ):
        super().__init__(storage)

    async def get_by_chat_id_with_offset_and_limit(
            self,
            chat_id: Chat.ExternalID,
            offset: int,
            limit: int,
    ) -> list[Message]:
        chat_messages: list[Message] = []

        for message in self._storage.values():
            if message.chat_id == chat_id:
                chat_messages.append(message)

        chat_messages.sort(key=lambda m: m.sequence_number.value)

        return chat_messages[offset:offset + limit]

    async def get_by_thread_id(
            self,
            thread_id: ID,
    ) -> list[Message]:
        thread_messages: list[Message] = []

        for message in self._storage.values():
            if message.thread_id == thread_id:
                thread_messages.append(message)

        thread_messages.sort(key=lambda m: m.sequence_number.value)

        return thread_messages
