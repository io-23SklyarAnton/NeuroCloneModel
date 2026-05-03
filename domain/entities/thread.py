__all__ = ["Thread"]

from typing import Optional, TYPE_CHECKING

import constants
from domain.entities.base import Aggregate
from domain.entities.message import Message
from domain.value_objects import ID, ValueObject

if TYPE_CHECKING:
    from domain.entities.chat import Chat


class Thread(Aggregate):
    class Summary(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Thread.Summary)

            return self.value == other.value

    def __init__(
            self,
            id_: ID,
            chat_id: "Chat.ExternalID",
            summary: Optional[Summary],
            last_summary_seq_num: Message.SequenceNumber,
            recent_messages: list[Message]
    ):
        super().__init__()
        self._id = id_
        self._chat_id = chat_id
        self._summary = summary
        self._last_summary_seq_num = last_summary_seq_num
        self._recent_messages = recent_messages

        self._messages_to_add: list[Message] = []

    @property
    def id(self) -> ID:
        return self._id

    @property
    def chat_id(self) -> "Chat.ExternalID":
        return self._chat_id

    @property
    def summary(self) -> Optional[Summary]:
        return self._summary

    @property
    def last_summary_seq_num(self) -> Message.SequenceNumber:
        return self._last_summary_seq_num

    @property
    def recent_messages(self) -> list[Message]:
        return self._recent_messages

    @property
    def uncommitted_messages(self) -> list[Message]:
        return self._messages_to_add

    @classmethod
    def create(
            cls,
            message: Message,
    ) -> "Thread":
        return cls(
            id_=ID.create(),
            chat_id=message.chat_id,
            summary=None,
            last_summary_seq_num=message.sequence_number,
            recent_messages=[message],
        )

    def add_message(
            self,
            message: Message,
    ) -> None:
        self._messages_to_add.append(message)

        self._recent_messages.append(message)
        self._recent_messages = self._recent_messages[-constants.N_RECENT_MESSAGES:]

    def needs_summary_update(self) -> bool:
        seq_num_diff = self._recent_messages[-1].sequence_number.value - self._last_summary_seq_num.value
        return (seq_num_diff + 1) >= constants.W_AGG

    def update_summary(
            self,
            summary: Summary,
    ) -> None:
        self._summary = summary
        self._last_summary_seq_num = self._recent_messages[-1].sequence_number
