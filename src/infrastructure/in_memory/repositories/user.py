from typing import Optional

from domain.entities.user import User
from domain.value_objects import ID
from features.interfaces.repositories.i_user import IUserRepository
from infrastructure.in_memory.repositories.base import InMemoryBaseRepository


class InMemoryUserRepository(InMemoryBaseRepository[User], IUserRepository):
    def __init__(
            self,
            storage: dict[ID, User],
    ):
        super().__init__(storage)

    async def get_by_id_or_raise(self, user_id: User.TelegramID) -> User:
        return self.get_or_raise(user_id)

    async def get_by_id_optional(self, user_id: User.TelegramID) -> Optional[User]:
        return self.get_optional(user_id)
