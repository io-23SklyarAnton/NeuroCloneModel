from typing import Optional

from domain.entities.chat import Chat
from features.interfaces.repositories.i_chat import IChatRepository
from infrastructure.in_memory.repositories.base import InMemoryBaseRepository


class InMemoryChatRepository(InMemoryBaseRepository[Chat], IChatRepository):
    def __init__(
            self,
            storage: dict[Chat.ExternalID, Chat],
    ):
        super().__init__(storage)

    async def get_by_id_or_raise(
            self,
            id_: Chat.ExternalID,
    ) -> Chat:
        return self.get_or_raise(id_)

    async def get_by_id_optional(
            self,
            chat_id: Chat.ExternalID,
    ) -> Optional[Chat]:
        return self.get_optional(chat_id)
