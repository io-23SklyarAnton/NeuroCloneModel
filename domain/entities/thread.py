__all__ = ["Thread"]

from typing import Optional

from domain.entities.base import Aggregate
from domain.entities.message import Message
from domain.value_objects import ID, ValueObject


class Thread(Aggregate):
    class Summary(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Thread.Summary)

            return self.value == other.value

    def __init__(
            self,
            id_: ID,
            summary: Optional[Summary],
            last_summary_seq_num: Message.SequenceNumber,
            recent_messages: list[Message]
    ):
        super().__init__()
        self._id = id_
        self._summary = summary
        self._last_summary_seq_num = last_summary_seq_num
        self._recent_messages = recent_messages

    @property
    def id(self) -> ID:
        return self._id

    @property
    def summary(self) -> Optional[Summary]:
        return self._summary

    @property
    def last_summary_seq_num(self) -> Message.SequenceNumber:
        return self._last_summary_seq_num

    @property
    def recent_messages(self) -> list[Message]:
        return self._recent_messages

    @classmethod
    def create(
            cls,
            message: Message,
    ) -> "Thread":
        return cls(
            id_=ID.create(),
            summary=None,
            last_summary_seq_num=message.sequence_number,
            recent_messages=[message],
        )
