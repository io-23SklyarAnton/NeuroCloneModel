__all__ = ["IBotRepository"]

import abc
from typing import Optional

from domain.entities.bot import Bot
from domain.value_objects import ID
from features.interfaces.repositories.i_base import IBaseRepository


class IBotRepository(IBaseRepository[Bot]):
    @abc.abstractmethod
    async def get_by_id_or_raise(self, bot_id: ID) -> Bot: ...

    @abc.abstractmethod
    async def get_by_id_optional(self, bot_id: ID) -> Optional[Bot]: ...

    @abc.abstractmethod
    async def get_by_token_optional(self, token: Bot.Token) -> Optional[Bot]: ...
