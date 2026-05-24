__all__ = [
    "BotRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from bot_operations.application.interfaces.repositories import IBotRepository
from bot_operations.domain.entities import Bot as BotAggregate
from bot_operations.infrastructure.db.models import Bot as DBBot
from common.domain.value_objects import ID
from common.exceptions.base import UnexpectedError
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository


class BotRepository(IBotRepository, BaseRepository[BotAggregate, DBBot]):
    @property
    def model(self) -> type[DBBot]:
        return DBBot

    async def get_by_id_or_raise(
            self,
            bot_id: ID,
    ) -> BotAggregate:
        bot: Optional[BotAggregate] = await self.get_by_id_optional(bot_id)
        if bot is None:
            raise UnexpectedError(f"Bot with id={bot_id.value} not found")

        return bot

    async def get_by_id_optional(
            self,
            bot_id: ID,
    ) -> Optional[BotAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_id(query, bot_id)

        db_bot: Optional[DBBot] = query.first()
        return self.get_optional(db_bot)

    async def get_by_token_optional(
            self,
            token: BotAggregate.Token,
    ) -> Optional[BotAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_token(query, token)

        db_bot: Optional[DBBot] = query.first()
        return self.get_optional(db_bot)

    async def get_by_owner_id(
            self,
            owner_id: BotAggregate.OwnerTelegramID,
    ) -> list[BotAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_owner_id(query, owner_id)

        db_bots: list[DBBot] = query.all()
        return self.get_all(db_bots)

    def from_aggregate_to_db_model(
            self,
            aggregate: BotAggregate,
    ) -> DBBot:
        return DBBot(
            id=aggregate.id.value,
            owner_telegram_id=aggregate.owner_id.value,
            token=aggregate.token.value,
            name=aggregate.name.value,
            status=aggregate.status,
            linked_dataset_ids=[
                linked_dataset_id.value.value
                for linked_dataset_id in aggregate.linked_dataset_ids
            ],
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBBot,
    ) -> BotAggregate:
        return BotAggregate(
            id_=ID(value=db_model.id),
            owner_id=BotAggregate.OwnerTelegramID(value=db_model.owner_telegram_id),
            token=BotAggregate.Token(value=db_model.token),
            name=BotAggregate.Name(value=db_model.name),
            status=db_model.status,
            linked_dataset_ids=[
                BotAggregate.LinkedDatasetID(value=ID(value=linked_dataset_id))
                for linked_dataset_id in db_model.linked_dataset_ids
            ],
        )

    def _filter_by_id(
            self,
            query: Query,
            bot_id: ID,
    ) -> Query:
        return query.filter(self.model.id == bot_id.value)

    def _filter_by_token(
            self,
            query: Query,
            token: BotAggregate.Token,
    ) -> Query:
        return query.filter(self.model.token == token.value)

    def _filter_by_owner_id(
            self,
            query: Query,
            owner_id: BotAggregate.OwnerTelegramID,
    ) -> Query:
        return query.filter(self.model.owner_telegram_id == owner_id.value)
