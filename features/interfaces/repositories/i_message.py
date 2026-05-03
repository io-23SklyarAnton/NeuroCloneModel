import abc

from domain.entities.chat import Chat
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
