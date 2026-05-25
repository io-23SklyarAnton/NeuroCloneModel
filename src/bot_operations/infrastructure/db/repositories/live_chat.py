__all__ = [
    "LiveChatRepository",
]

from typing import Optional

from sqlalchemy.orm import Query, joinedload

from bot_operations.application.interfaces.repositories import ILiveChatRepository
from bot_operations.domain.entities import LiveChat as LiveChatAggregate
from bot_operations.domain.entities import LiveMessage
from bot_operations.infrastructure.db.models import LiveChat as DBLiveChat
from bot_operations.infrastructure.db.models import LiveMessage as DBLiveMessage
from common.domain.value_objects import ID, UserName
from common.exceptions.base import UnexpectedError
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository


class LiveChatRepository(ILiveChatRepository, BaseRepository[LiveChatAggregate, DBLiveChat]):
    @property
    def model(self) -> type[DBLiveChat]:
        return DBLiveChat

    def base_query(self) -> Query:
        query: Query = super().base_query()
        return query.options(joinedload(DBLiveChat.recent_messages))

    async def get_by_id_or_raise(
            self,
            external_id: LiveChatAggregate.ExternalID,
    ) -> LiveChatAggregate:
        live_chat: Optional[LiveChatAggregate] = await self.get_by_id_optional(external_id)
        if live_chat is None:
            raise UnexpectedError(f"LiveChat with external_id={external_id.value} not found")

        return live_chat

    async def get_by_id_optional(
            self,
            external_id: LiveChatAggregate.ExternalID,
    ) -> Optional[LiveChatAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_external_id(query, external_id)

        db_live_chat: Optional[DBLiveChat] = query.first()
        return self.get_optional(db_live_chat)

    def from_aggregate_to_db_model(
            self,
            aggregate: LiveChatAggregate,
    ) -> DBLiveChat:
        return DBLiveChat(
            external_id=aggregate.external_id.value,
            bot_id=aggregate.bot_id.value,
            recent_messages=[
                self._live_message_to_db_model(
                    message=message,
                    live_chat_external_id=aggregate.external_id.value,
                )
                for message in aggregate.recent_messages
            ],
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBLiveChat,
    ) -> LiveChatAggregate:
        return LiveChatAggregate(
            external_id=LiveChatAggregate.ExternalID(value=db_model.external_id),
            bot_id=ID(value=db_model.bot_id),
            recent_messages=[
                self._db_model_to_live_message(db_message)
                for db_message in db_model.recent_messages
            ],
        )

    @staticmethod
    def _live_message_to_db_model(
            message: LiveMessage,
            live_chat_external_id: int,
    ) -> DBLiveMessage:
        return DBLiveMessage(
            id=message.id.value,
            live_chat_external_id=live_chat_external_id,
            from_user=message.from_user.value,
            text=message.text.value,
            sent_at=message.sent_at.replace(tzinfo=None),
            is_from_bot=message.is_from_bot,
        )

    @staticmethod
    def _db_model_to_live_message(
            db_model: DBLiveMessage,
    ) -> LiveMessage:
        return LiveMessage(
            id_=ID(value=db_model.id),
            from_user=UserName(value=db_model.from_user),
            text=LiveMessage.Text(value=db_model.text),
            sent_at=db_model.sent_at,
            is_from_bot=db_model.is_from_bot,
        )

    def _filter_by_external_id(
            self,
            query: Query,
            external_id: LiveChatAggregate.ExternalID,
    ) -> Query:
        return query.filter(self.model.external_id == external_id.value)
