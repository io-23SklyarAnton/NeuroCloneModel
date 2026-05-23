__all__ = ["InMemoryLiveChatRepository"]

from typing import Optional

from bot_operations.application.interfaces.repositories import ILiveChatRepository
from bot_operations.domain.entities import LiveChat
from common.infrastructure.in_memory_repository import InMemoryBaseRepository


class InMemoryLiveChatRepository(InMemoryBaseRepository[LiveChat], ILiveChatRepository):
    def __init__(
            self,
            storage: dict[LiveChat.ExternalID, LiveChat],
    ):
        super().__init__(storage)

    async def get_by_id_or_raise(
            self,
            external_id: LiveChat.ExternalID,
    ) -> LiveChat:
        return self.get_or_raise(external_id)

    async def get_by_id_optional(
            self,
            external_id: LiveChat.ExternalID,
    ) -> Optional[LiveChat]:
        return self.get_optional(external_id)
