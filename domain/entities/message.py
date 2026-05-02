__all__ = ["Message"]

from typing import Optional

from domain.entities.base import Aggregate
from domain.value_objects import ID, ValueObject, DateUnixtime


class Message(Aggregate):
    class ExternalID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Message.ExternalID)

            return self.value == other.value

    class SequenceNumber(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Message.SequenceNumber)

            return self.value == other.value

    class UserName(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Message.UserName)

            return self.value == other.value

    class Text(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Message.Text)

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
    ):
        super().__init__()
        self._id = id_
        self._external_id = external_id
        self._reply_to_message_id = reply_to_message_id
        self._sequence_number = sequence_number
        self._date_unixtime = date_unixtime
        self._from_user = from_user
        self._text = text

    @property
    def id(self) -> ID:
        return self._id

    @property
    def reply_to_message_id(self) -> Optional[ID]:
        return self._reply_to_message_id

    @property
    def external_id(self) -> ExternalID:
        return self._external_id

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

    def has_reply_message_id(self):
        return self._reply_to_message_id is not None
