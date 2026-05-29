__all__ = [
    "ChatExportRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from common.domain.value_objects import FileReference, OwnerTelegramID, UserName
from common.exceptions.base import UnexpectedError
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository
from data_preparation.application.interfaces.repositories import IChatExportRepository
from data_preparation.domain.entities import ChatExport as ChatExportAggregate
from data_preparation.infrastructure.db.models import ChatExport as DBChatExport


class ChatExportRepository(IChatExportRepository, BaseRepository[ChatExportAggregate, DBChatExport]):
    @property
    def model(self) -> type[DBChatExport]:
        return DBChatExport

    async def get_by_id_or_raise(
            self,
            chat_id: ChatExportAggregate.ChatID,
    ) -> ChatExportAggregate:
        chat_export: Optional[ChatExportAggregate] = await self.get_by_id_optional(chat_id)
        if chat_export is None:
            raise UnexpectedError(f"ChatExport with chat_id={chat_id.value} not found")

        return chat_export

    async def get_by_id_optional(
            self,
            chat_id: ChatExportAggregate.ChatID,
    ) -> Optional[ChatExportAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_chat_id(query, chat_id)

        db_chat_export: Optional[DBChatExport] = query.first()
        return self.get_optional(db_chat_export)

    def from_aggregate_to_db_model(
            self,
            aggregate: ChatExportAggregate,
    ) -> DBChatExport:
        return DBChatExport(
            chat_id=aggregate.chat_id.value,
            owner_telegram_id=aggregate.owner_id.value,
            target_user_name=aggregate.target_user_name.value,
            file_bucket=aggregate.file_reference.bucket,
            file_key=aggregate.file_reference.key,
            status=aggregate.status,
            n_messages=aggregate.n_messages,
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBChatExport,
    ) -> ChatExportAggregate:
        return ChatExportAggregate(
            chat_id=ChatExportAggregate.ChatID(value=db_model.chat_id),
            owner_id=OwnerTelegramID(value=db_model.owner_telegram_id),
            target_user_name=UserName(value=db_model.target_user_name),
            file_reference=FileReference(
                bucket=db_model.file_bucket,
                key=db_model.file_key,
            ),
            status=db_model.status,
            n_messages=db_model.n_messages,
        )

    def _filter_by_chat_id(
            self,
            query: Query,
            chat_id: ChatExportAggregate.ChatID,
    ) -> Query:
        return query.filter(self.model.chat_id == chat_id.value)
