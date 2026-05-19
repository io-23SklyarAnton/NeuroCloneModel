from typing import Optional

from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.entities.thread import Thread
from domain.value_objects import ID
from features.interfaces.repositories.i_thread import IThreadRepository
from infrastructure.in_memory.repositories.base import InMemoryBaseRepository


class InMemoryThreadRepository(InMemoryBaseRepository[Thread], IThreadRepository):
    def __init__(
            self,
            messages_storage: dict[ID, Message],
            storage: dict[ID, Thread],
    ):
        super().__init__(storage)
        self._messages_storage = messages_storage

    async def get_by_message_id(
            self,
            message_id: Message.ExternalID,
    ) -> Optional[Thread]:
        target_thread_id: Optional[ID] = None

        for message in self._messages_storage.values():
            if message.id == message_id:
                target_thread_id = message.thread_id
                break

        if target_thread_id is None:
            return None

        return self.get_or_raise(id_=target_thread_id)

    async def get_all_by_chat_id(
            self,
            chat_id: Chat.ExternalID,
    ) -> list[Thread]:
        chat_threads: list[Thread] = []

        for thread in self._storage.values():
            if thread.chat_id == chat_id:
                chat_threads.append(thread)

        return chat_threads
