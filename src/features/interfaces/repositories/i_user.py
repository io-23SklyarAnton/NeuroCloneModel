__all__ = ["IUserRepository"]

import abc
from typing import Optional

from domain.entities.user import User
from features.interfaces.repositories.i_base import IBaseRepository


class IUserRepository(IBaseRepository[User]):
    @abc.abstractmethod
    async def get_by_id_or_raise(self, user_id: User.TelegramID) -> User: ...

    @abc.abstractmethod
    async def get_by_id_optional(self, user_id: User.TelegramID) -> Optional[User]: ...

