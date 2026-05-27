__all__ = [
    "ThreadRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from common.domain.value_objects import ID, UserName
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository
from data_preparation.application import constants
from data_preparation.application.interfaces.repositories import IThreadRepository
from data_preparation.domain.entities import ChatExport, ParsedMessage, Thread as ThreadAggregate
from data_preparation.domain.value_objects import DateUnixtime
from data_preparation.infrastructure.db.models import ParsedMessage as DBParsedMessage
from data_preparation.infrastructure.db.models import Thread as DBThread


class ThreadRepository(IThreadRepository, BaseRepository[ThreadAggregate, DBThread]):
    @property
    def model(self) -> type[DBThread]:
        return DBThread

    async def get_by_id_optional(
            self,
            thread_id: ID,
    ) -> Optional[ThreadAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_id(query, thread_id)

        db_thread: Optional[DBThread] = query.first()
        if db_thread is None:
            return None

        return self._build_aggregate_with_recent_messages(db_thread)

    async def get_all_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> list[ThreadAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_chat_export_id(query, chat_export_id)

        db_threads: list[DBThread] = query.all()
        return [
            self._build_aggregate_with_recent_messages(db_thread)
            for db_thread in db_threads
        ]

    def from_aggregate_to_db_model(
            self,
            aggregate: ThreadAggregate,
    ) -> DBThread:
        return DBThread(
            id=aggregate.id.value,
            chat_export_id=aggregate.chat_export_id.value,
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBThread,
    ) -> ThreadAggregate:
        return ThreadAggregate(
            id_=ID(value=db_model.id),
            chat_export_id=ChatExport.ChatID(value=db_model.chat_export_id),
            recent_messages=[],
        )

    def _build_aggregate_with_recent_messages(
            self,
            db_thread: DBThread,
    ) -> ThreadAggregate:
        recent_messages_query: Query = (
            self._session.query(DBParsedMessage)
            .filter(DBParsedMessage.thread_id == db_thread.id)
            .order_by(DBParsedMessage.sequence_number.desc())
            .limit(constants.N_RECENT_MESSAGES)
        )
        db_messages: list[DBParsedMessage] = list(reversed(recent_messages_query.all()))

        return ThreadAggregate(
            id_=ID(value=db_thread.id),
            chat_export_id=ChatExport.ChatID(value=db_thread.chat_export_id),
            recent_messages=[
                self._db_message_to_parsed_message(db_message)
                for db_message in db_messages
            ],
        )

    @staticmethod
    def _db_message_to_parsed_message(
            db_model: DBParsedMessage,
    ) -> ParsedMessage:
        return ParsedMessage(
            id_=ID(value=db_model.id),
            external_id=ParsedMessage.ExternalID(value=db_model.external_id),
            reply_to_message_id=(
                ID(value=db_model.reply_to_message_id)
                if db_model.reply_to_message_id is not None else None
            ),
            sequence_number=ParsedMessage.SequenceNumber(value=db_model.sequence_number),
            date_unixtime=DateUnixtime(value=db_model.date_unixtime),
            from_user=UserName(value=db_model.from_user),
            text=ParsedMessage.Text(value=db_model.text),
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
            thread_id: ID,
    ) -> Query:
        return query.filter(self.model.id == thread_id.value)

    def _filter_by_chat_export_id(
            self,
            query: Query,
            chat_export_id: ChatExport.ChatID,
    ) -> Query:
        return query.filter(self.model.chat_export_id == chat_export_id.value)
