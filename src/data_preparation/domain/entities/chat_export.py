__all__ = ["ChatExport"]

from enum import StrEnum

from common.domain.entities import Aggregate
from common.domain.value_objects import ValueObject, UserName
from data_preparation.domain.value_objects import ExportFileKey


class ChatExport(Aggregate):
    class Status(StrEnum):
        PENDING = "PENDING"
        INGESTED = "INGESTED"
        READY = "READY"
        FAILED = "FAILED"

    class ChatID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, ChatExport.ChatID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    class OwnerTelegramID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, ChatExport.OwnerTelegramID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    class IllegalStateTransitionError(RuntimeError):
        def __init__(
                self,
                current: "ChatExport.Status",
                requested: "ChatExport.Status",
        ) -> None:
            super().__init__(f"Illegal chat export status transition: {current.value} -> {requested.value}")

    class EventChatExportCreated(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            export_file_key: ExportFileKey

    class EventChatExportIngested(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            pass

    class EventChatExportReady(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            pass

    class EventChatExportFailed(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            pass

    def __init__(
            self,
            chat_id: ChatID,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            export_file_key: ExportFileKey,
            status: Status,
            n_messages: int,
    ):
        super().__init__()
        self._chat_id = chat_id
        self._owner_id = owner_id
        self._target_user_name = target_user_name
        self._export_file_key = export_file_key
        self._status = status
        self._n_messages = n_messages

    @property
    def id(self) -> ChatID:
        return self._chat_id

    @property
    def chat_id(self) -> ChatID:
        return self._chat_id

    @property
    def owner_id(self) -> OwnerTelegramID:
        return self._owner_id

    @property
    def target_user_name(self) -> UserName:
        return self._target_user_name

    @property
    def export_file_key(self) -> ExportFileKey:
        return self._export_file_key

    @property
    def status(self) -> Status:
        return self._status

    @property
    def n_messages(self) -> int:
        return self._n_messages

    @classmethod
    def create(
            cls,
            chat_id: ChatID,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            export_file_key: ExportFileKey,
    ) -> "ChatExport":
        chat_export = cls(
            chat_id=chat_id,
            owner_id=owner_id,
            target_user_name=target_user_name,
            export_file_key=export_file_key,
            status=cls.Status.PENDING,
            n_messages=0,
        )
        chat_export._events_to_publish.append(cls.EventChatExportCreated(
            object_id=str(chat_export.id.value),
            payload=cls.EventChatExportCreated.Payload(
                export_file_key=export_file_key,
            ),
        ))
        return chat_export

    def record_message_count(
            self,
            n_messages: int,
    ) -> None:
        self._n_messages = n_messages

    def mark_ingested(self) -> None:
        if self._status != self.Status.PENDING:
            raise ChatExport.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.INGESTED,
            )
        self._status = self.Status.INGESTED

        self._events_to_publish.append(ChatExport.EventChatExportIngested(
            object_id=str(self._chat_id.value),
        ))

    def mark_ready(self) -> None:
        if self._status != self.Status.INGESTED:
            raise ChatExport.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.READY,
            )
        self._status = self.Status.READY

        self._events_to_publish.append(ChatExport.EventChatExportReady(
            object_id=str(self._chat_id.value),
        ))

    def mark_failed(self) -> None:
        self._status = self.Status.FAILED

        self._events_to_publish.append(ChatExport.EventChatExportFailed(
            object_id=str(self._chat_id.value),
        ))
