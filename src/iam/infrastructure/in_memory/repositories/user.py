__all__ = ["InMemoryUserRepository"]

from typing import Optional

from common.infrastructure.in_memory_repository import InMemoryBaseRepository
from iam.application.interfaces.repositories import IUserRepository
from iam.domain.entities import User


class InMemoryUserRepository(InMemoryBaseRepository[User], IUserRepository):
    def __init__(
            self,
            storage: dict[User.TelegramID, User],
    ):
        super().__init__(storage)

    async def get_by_id_or_raise(self, user_id: User.TelegramID) -> User:
        return self.get_or_raise(user_id)

    async def get_by_id_optional(self, user_id: User.TelegramID) -> Optional[User]:
        return self.get_optional(user_id)
