__all__ = ["IBotRepository"]

import abc
from typing import Optional

from bot_operations.domain.entities import Bot
from common.domain.value_objects import ID, UserName
from common.infrastructure.db.i_base_repository import IBaseRepository


class IBotRepository(IBaseRepository[Bot]):
    @abc.abstractmethod
    async def get_by_id_or_raise(self, bot_id: ID) -> Bot: ...

    @abc.abstractmethod
    async def get_by_id_optional(self, bot_id: ID) -> Optional[Bot]: ...

    @abc.abstractmethod
    async def get_by_token_optional(self, token: Bot.Token) -> Optional[Bot]: ...

    @abc.abstractmethod
    async def get_by_owner_id(self, owner_id: Bot.OwnerTelegramID) -> list[Bot]: ...

    @abc.abstractmethod
    async def get_by_owner_and_target_user(
            self,
            owner_id: Bot.OwnerTelegramID,
            target_user_name: UserName,
    ) -> list[Bot]: ...
