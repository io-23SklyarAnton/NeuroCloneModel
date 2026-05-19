import abc
from typing import Optional

from domain.entities.chat import Chat
from features.interfaces.repositories import IBaseRepository


class IChatRepository(IBaseRepository):
    @abc.abstractmethod
    async def get_by_id_or_raise(
            self,
            chat_id: Chat.ExternalID,
    ) -> Chat:
        pass

    @abc.abstractmethod
    async def get_by_id_optional(
            self,
            chat_id: Chat.ExternalID,
    ) -> Optional[Chat]:
        pass
