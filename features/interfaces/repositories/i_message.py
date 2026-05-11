import abc

from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.value_objects import ID
from features.interfaces.repositories import IBaseRepository


class IMessageRepository(IBaseRepository):
    @abc.abstractmethod
    def get_by_chat_id_with_offset_and_limit(
            self,
            chat_id: Chat.ExternalID,
            offset: int,
            limit: int
    ):
        pass

    @abc.abstractmethod
    async def get_by_thread_id(
            self,
            thread_id: ID,
    ) -> list[Message]:
        pass
