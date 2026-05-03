from typing import Optional, Any

from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.entities.thread import Thread
from domain.value_objects import ID
from features.interfaces.repositories.i_thread import IThreadRepository
from infrastructure.in_memory.base import InMemoryBaseRepository


class InMemoryThreadRepository(InMemoryBaseRepository[Thread], IThreadRepository):
    def __init__(
            self,
            messages_storage: dict[ID, Message],
            storage: dict[ID, Thread],
    ):
        super().__init__(storage)
        self._messages_storage = messages_storage

    async def get_by_message_external_id_and_chat_id(
            self,
            message_external_id: Message.ExternalID,
            chat_id: Chat.ExternalID,
    ) -> Optional[Thread]:
        target_thread_id: Optional[ID] = None

        for message in self._messages_storage.values():
            if message.external_id == message_external_id and message.chat_id == chat_id:
                target_thread_id = message.thread_id
                break

        if target_thread_id is None:
            return None

        return self.get_or_raise(id_=target_thread_id)
