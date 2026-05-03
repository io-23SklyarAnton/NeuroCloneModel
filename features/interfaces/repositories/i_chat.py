import abc

from domain.entities.chat import Chat
from features.interfaces.repositories import IBaseRepository


class IChatRepository(IBaseRepository):
    @abc.abstractmethod
    def get_by_id_or_raise(self, chat_id: Chat.ExternalID):
        pass
