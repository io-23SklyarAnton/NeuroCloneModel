import abc

from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.entities.thread import Thread
from features.interfaces.repositories import IBaseRepository


class IThreadRepository(IBaseRepository):
    @abc.abstractmethod
    def get_by_message_external_id_and_chat_id(
            self,
            message_external_id: Message.ExternalID,
            chat_id: Chat.ExternalID,
    ):
        pass

    @abc.abstractmethod
    async def get_all_by_chat_id(
            self,
            chat_id: Chat.ExternalID,
    ) -> list[Thread]:
        pass
