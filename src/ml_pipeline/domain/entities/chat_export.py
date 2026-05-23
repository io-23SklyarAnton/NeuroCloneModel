__all__ = [
    "ChatExport",
    "ParsedMessage",
]

from enum import StrEnum
from typing import Optional

from common.domain.entities import Aggregate, Entity
from common.domain.value_objects import ID, ValueObject
from ml_pipeline.domain.value_objects import DateUnixtime, ExportFileKey


class ParsedMessage(Entity):
    class Type(StrEnum):
        TEXT = "TEXT"
        IMAGE = "IMAGE"
        VIDEO_FILE = "VIDEO_FILE"
        VOICE_MESSAGE = "VOICE_MESSAGE"
        VIDEO_MESSAGE = "VIDEO_MESSAGE"
        STICKER = "STICKER"
        ANIMATION = "ANIMATION"
        AUDIO_FILE = "AUDIO_FILE"
        FILE = "FILE"
        LOCATION = "LOCATION"
        POLL = "POLL"
        OTHER_MEDIA = "OTHER_MEDIA"
        SERVICE = "SERVICE"

    class ExternalID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, ParsedMessage.ExternalID)

            return self.value == other.value

    class SequenceNumber(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, ParsedMessage.SequenceNumber)

            return self.value == other.value

    class UserName(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, ParsedMessage.UserName)

            return self.value == other.value

    class Text(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, ParsedMessage.Text)

            return self.value == other.value

    def __init__(
            self,
            id_: ID,
            external_id: ExternalID,
            reply_to_message_id: Optional[ID],
            sequence_number: SequenceNumber,
            date_unixtime: DateUnixtime,
            from_user: UserName,
            text: Text,
            chat_export_id: "ChatExport.ChatID",
            thread_id: Optional[ID],
            message_type: Type,
    ):
        self._id = id_
        self._external_id = external_id
        self._reply_to_message_id = reply_to_message_id
        self._sequence_number = sequence_number
        self._date_unixtime = date_unixtime
        self._from_user = from_user
        self._text = text
        self._chat_export_id = chat_export_id
        self._thread_id = thread_id
        self._message_type = message_type

    @property
    def id(self) -> ID:
        return self._id

    @property
    def external_id(self) -> ExternalID:
        return self._external_id

    @property
    def reply_to_message_id(self) -> Optional[ID]:
        return self._reply_to_message_id

    @property
    def sequence_number(self) -> SequenceNumber:
        return self._sequence_number

    @property
    def date_unixtime(self) -> DateUnixtime:
        return self._date_unixtime

    @property
    def from_user(self) -> UserName:
        return self._from_user

    @property
    def text(self) -> Text:
        return self._text

    @property
    def chat_export_id(self) -> "ChatExport.ChatID":
        return self._chat_export_id

    @property
    def thread_id(self) -> Optional[ID]:
        return self._thread_id

    @property
    def message_type(self) -> Type:
        return self._message_type

    def has_reply_message_id(self) -> bool:
        return self._reply_to_message_id is not None

    @classmethod
    def create(
            cls,
            external_id: ExternalID,
            reply_to_message_id: Optional[ID],
            sequence_number: SequenceNumber,
            date_unixtime: DateUnixtime,
            from_user: UserName,
            text: Text,
            chat_export_id: "ChatExport.ChatID",
            message_type: Type,
    ) -> "ParsedMessage":
        return cls(
            id_=ID.create(),
            external_id=external_id,
            reply_to_message_id=reply_to_message_id,
            sequence_number=sequence_number,
            date_unixtime=date_unixtime,
            from_user=from_user,
            text=text,
            chat_export_id=chat_export_id,
            thread_id=None,
            message_type=message_type,
        )

    def assign_to_thread(
            self,
            thread_id: ID,
    ) -> None:
        if self._thread_id is not None:
            raise ValueError(f"Message {self._id} already belongs to thread {self._thread_id}")

        self._thread_id = thread_id


class ChatExport(Aggregate):
    class Status(StrEnum):
        PENDING = "PENDING"
        DISENTANGLING = "DISENTANGLING"
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

    def __init__(
            self,
            chat_id: ChatID,
            owner_id: OwnerTelegramID,
            export_file_key: ExportFileKey,
            status: Status,
            parsed_messages: list[ParsedMessage],
    ):
        super().__init__()
        self._chat_id = chat_id
        self._owner_id = owner_id
        self._export_file_key = export_file_key
        self._status = status
        self._parsed_messages = parsed_messages

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
    def export_file_key(self) -> ExportFileKey:
        return self._export_file_key

    @property
    def status(self) -> Status:
        return self._status

    @property
    def parsed_messages(self) -> list[ParsedMessage]:
        return self._parsed_messages

    @property
    def n_messages(self) -> int:
        return len(self._parsed_messages)

    @classmethod
    def create(
            cls,
            chat_id: ChatID,
            owner_id: OwnerTelegramID,
            export_file_key: ExportFileKey,
    ) -> "ChatExport":
        chat_export = cls(
            chat_id=chat_id,
            owner_id=owner_id,
            export_file_key=export_file_key,
            status=cls.Status.PENDING,
            parsed_messages=[],
        )
        chat_export._events_to_publish.append(cls.EventChatExportCreated(
            object_id=str(chat_export.id.value),
            payload=cls.EventChatExportCreated.Payload(
                export_file_key=export_file_key,
            ),
        ))
        return chat_export

    def attach_parsed_messages(
            self,
            parsed_messages: list[ParsedMessage],
    ) -> None:
        if self._parsed_messages:
            raise ValueError(f"Chat export {self._chat_id} already has parsed messages")

        self._parsed_messages = parsed_messages

    def mark_disentangling(self) -> None:
        if self._status != self.Status.PENDING:
            raise ChatExport.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.DISENTANGLING,
            )

        self._status = self.Status.DISENTANGLING

    def mark_ready(self) -> None:
        if self._status != self.Status.DISENTANGLING:
            raise ChatExport.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.READY,
            )

        self._status = self.Status.READY

    def mark_failed(self) -> None:
        self._status = self.Status.FAILED
