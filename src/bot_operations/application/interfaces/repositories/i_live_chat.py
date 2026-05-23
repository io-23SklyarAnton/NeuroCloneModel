__all__ = ["ILiveChatRepository"]

import abc
from typing import Optional

from bot_operations.domain.entities import LiveChat
from common.infrastructure.i_base_repository import IBaseRepository


class ILiveChatRepository(IBaseRepository[LiveChat]):
    @abc.abstractmethod
    async def get_by_id_or_raise(
            self,
            external_id: LiveChat.ExternalID,
    ) -> LiveChat: ...

    @abc.abstractmethod
    async def get_by_id_optional(
            self,
            external_id: LiveChat.ExternalID,
    ) -> Optional[LiveChat]: ...
