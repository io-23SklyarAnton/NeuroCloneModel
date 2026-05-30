__all__ = [
    "ParsedMessageRepository",
]

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Query

from common.domain.value_objects import ID, UserName
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository
from common.infrastructure.db.models import OutboxMessage
from data_preparation.application.interfaces.repositories import IParsedMessageRepository
from data_preparation.domain.entities import ChatExport, ParsedMessage as ParsedMessageAggregate
from data_preparation.domain.value_objects import DateUnixtime
from data_preparation.infrastructure.db.models import ParsedMessage as DBParsedMessage


class ParsedMessageRepository(
        IParsedMessageRepository,
        BaseRepository[ParsedMessageAggregate, DBParsedMessage],
):
    @property
    def model(self) -> type[DBParsedMessage]:
        return DBParsedMessage

    def create_many(
            self,
            messages: list[ParsedMessageAggregate],
    ) -> None:
        db_messages: list[DBParsedMessage] = [
            self.from_aggregate_to_db_model(message)
            for message in messages
        ]
        self._session.add_all(db_messages)

        outbox_messages: list[OutboxMessage] = []
        for message in messages:
            for event in message.publish_events():
                outbox_messages.append(OutboxMessage(
                    id=event.id,
                    object_id=event.object_id,
                    name=event.__class__.__name__,
                    data=event.payload.model_dump(mode="json"),
                ))

        if outbox_messages:
            self._session.add_all(outbox_messages)

    async def get_by_id_optional(
            self,
            message_id: ID,
    ) -> Optional[ParsedMessageAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_id(query, message_id)

        db_message: Optional[DBParsedMessage] = query.first()
        return self.get_optional(db_message)

    async def get_batch_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
            offset: int,
            limit: int,
    ) -> list[ParsedMessageAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_chat_export_id(query, chat_export_id)
        query = query.order_by(self.model.sequence_number.asc())
        query = query.offset(offset).limit(limit)

        db_messages: list[DBParsedMessage] = query.all()
        return self.get_all(db_messages)

    async def get_all_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> list[ParsedMessageAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_chat_export_id(query, chat_export_id)
        query = query.order_by(self.model.sequence_number.asc())

        db_messages: list[DBParsedMessage] = query.all()
        return self.get_all(db_messages)

    async def get_by_thread_id(
            self,
            thread_id: ID,
    ) -> list[ParsedMessageAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_thread_id(query, thread_id)
        query = query.order_by(self.model.sequence_number.asc())

        db_messages: list[DBParsedMessage] = query.all()
        return self.get_all(db_messages)

    async def get_by_chat_and_external_id_optional(
            self,
            chat_export_id: ChatExport.ChatID,
            external_id: ParsedMessageAggregate.ExternalID,
    ) -> Optional[ParsedMessageAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_chat_export_id(query, chat_export_id)
        query = self._filter_by_external_id(query, external_id)

        db_message: Optional[DBParsedMessage] = query.first()
        return self.get_optional(db_message)

    async def count_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> int:
        query: Query = self._session.query(func.count(self.model.id))

        query = self._filter_by_chat_export_id(query, chat_export_id)

        return int(query.scalar() or 0)

    def from_aggregate_to_db_model(
            self,
            aggregate: ParsedMessageAggregate,
    ) -> DBParsedMessage:
        return DBParsedMessage(
            id=aggregate.id.value,
            external_id=aggregate.external_id.value,
            reply_to_message_id=(
                aggregate.reply_to_message_id.value
                if aggregate.reply_to_message_id is not None else None
            ),
            sequence_number=aggregate.sequence_number.value,
            date_unixtime=aggregate.date_unixtime.value,
            from_user=aggregate.from_user.value,
            text=aggregate.text.value,
            chat_export_id=aggregate.chat_export_id.value,
            thread_id=(
                aggregate.thread_id.value
                if aggregate.thread_id is not None else None
            ),
            message_type=aggregate.message_type,
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBParsedMessage,
    ) -> ParsedMessageAggregate:
        return ParsedMessageAggregate(
            id_=ID(value=db_model.id),
            external_id=ParsedMessageAggregate.ExternalID(value=db_model.external_id),
            reply_to_message_id=(
                ID(value=db_model.reply_to_message_id)
                if db_model.reply_to_message_id is not None else None
            ),
            sequence_number=ParsedMessageAggregate.SequenceNumber(value=db_model.sequence_number),
            date_unixtime=DateUnixtime(value=db_model.date_unixtime),
            from_user=UserName(value=db_model.from_user),
            text=ParsedMessageAggregate.Text(value=db_model.text),
            chat_export_id=ChatExport.ChatID(value=db_model.chat_export_id),
            thread_id=(
                ID(value=db_model.thread_id)
                if db_model.thread_id is not None else None
            ),
            message_type=db_model.message_type,
        )

    def _filter_by_id(
            self,
            query: Query,
            message_id: ID,
    ) -> Query:
        return query.filter(self.model.id == message_id.value)

    def _filter_by_external_id(
            self,
            query: Query,
            external_id: ParsedMessageAggregate.ExternalID,
    ) -> Query:
        return query.filter(self.model.external_id == external_id.value)

    def _filter_by_chat_export_id(
            self,
            query: Query,
            chat_export_id: ChatExport.ChatID,
    ) -> Query:
        return query.filter(self.model.chat_export_id == chat_export_id.value)

    def _filter_by_thread_id(
            self,
            query: Query,
            thread_id: ID,
    ) -> Query:
        return query.filter(self.model.thread_id == thread_id.value)
