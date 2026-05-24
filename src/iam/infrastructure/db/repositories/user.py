__all__ = [
    "UserRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from common.exceptions.base import UnexpectedError
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository
from iam.application.interfaces.repositories import IUserRepository
from iam.domain.entities import User as UserAggregate
from iam.infrastructure.db.models import User as DBUser


class UserRepository(
        IUserRepository,
        BaseRepository[UserAggregate, DBUser],
):
    @property
    def model(self) -> type[DBUser]:
        return DBUser

    async def get_by_id_or_raise(
            self,
            user_id: UserAggregate.TelegramID,
    ) -> UserAggregate:
        user: Optional[UserAggregate] = await self.get_by_id_optional(user_id)
        if user is None:
            raise UnexpectedError(f"User with telegram_id={user_id.value} not found")

        return user

    async def get_by_id_optional(
            self,
            user_id: UserAggregate.TelegramID,
    ) -> Optional[UserAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_telegram_id(query, user_id)

        db_user: Optional[DBUser] = query.first()
        return self.get_optional(db_user)

    def from_aggregate_to_db_model(
            self,
            aggregate: UserAggregate,
    ) -> DBUser:
        return DBUser(
            telegram_id=aggregate.telegram_id.value,
            username=(
                aggregate.username.value
                if aggregate.username is not None else None
            ),
            registered_at=aggregate.registered_at.replace(tzinfo=None),
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBUser,
    ) -> UserAggregate:
        return UserAggregate(
            telegram_id=UserAggregate.TelegramID(value=db_model.telegram_id),
            username=(
                UserAggregate.Username(value=db_model.username)
                if db_model.username is not None else None
            ),
            registered_at=db_model.registered_at,
        )

    def _filter_by_telegram_id(
            self,
            query: Query,
            telegram_id: UserAggregate.TelegramID,
    ) -> Query:
        return query.filter(self.model.telegram_id == telegram_id.value)
