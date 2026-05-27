__all__ = ["ParsedMessage"]

from enum import StrEnum
from typing import Optional

from common.domain.entities import Aggregate
from common.domain.value_objects import ID, ValueObject, UserName
from data_preparation.domain.entities.chat_export import ChatExport
from data_preparation.domain.value_objects import DateUnixtime


class ParsedMessage(Aggregate):
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
            chat_export_id: ChatExport.ChatID,
            thread_id: Optional[ID],
            message_type: Type,
    ):
        super().__init__()
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
    def chat_export_id(self) -> ChatExport.ChatID:
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
            chat_export_id: ChatExport.ChatID,
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
