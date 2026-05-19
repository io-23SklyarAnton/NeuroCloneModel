__all__ = ["Thread"]

from typing import TYPE_CHECKING

import constants
from domain.entities.base import Aggregate
from domain.entities.message import Message
from domain.value_objects import ID

if TYPE_CHECKING:
    from domain.entities.chat import Chat


class Thread(Aggregate):
    def __init__(
            self,
            id_: ID,
            chat_id: "Chat.ExternalID",
            recent_messages: list[Message]
    ):
        super().__init__()
        self._id = id_
        self._chat_id = chat_id
        self._recent_messages = recent_messages

        self._messages_to_add: list[Message] = []

    @property
    def id(self) -> ID:
        return self._id

    @property
    def chat_id(self) -> "Chat.ExternalID":
        return self._chat_id

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
            recent_messages=[],
        )

    def add_message(
            self,
            message: Message,
    ) -> None:
        self._messages_to_add.append(message)

        self._recent_messages.append(message)
        self._recent_messages = self._recent_messages[-constants.N_RECENT_MESSAGES:]
