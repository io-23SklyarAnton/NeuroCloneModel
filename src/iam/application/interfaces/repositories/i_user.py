__all__ = ["IUserRepository"]

import abc
from typing import Optional

from common.infrastructure.i_base_repository import IBaseRepository
from iam.domain.entities import User


class IUserRepository(IBaseRepository[User]):
    @abc.abstractmethod
    async def get_by_id_or_raise(self, user_id: User.TelegramID) -> User: ...

    @abc.abstractmethod
    async def get_by_id_optional(self, user_id: User.TelegramID) -> Optional[User]: ...
