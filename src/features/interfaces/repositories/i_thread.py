import abc

from domain.entities.chat import Chat
from domain.entities.thread import Thread
from domain.value_objects import ID
from features.interfaces.repositories import IBaseRepository


class IThreadRepository(IBaseRepository):
    @abc.abstractmethod
    def get_by_message_id(
            self,
            message_id: ID,
    ):
        pass

    @abc.abstractmethod
    async def get_all_by_chat_id(
            self,
            chat_id: Chat.ExternalID,
    ) -> list[Thread]:
        pass
