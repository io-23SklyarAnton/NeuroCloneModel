__all__ = [
    "LiveChat",
    "LiveMessage",
]

from datetime import datetime

from common.domain.entities import Aggregate, Entity
from common.domain.value_objects import ID, ValueObject


class LiveMessage(Entity):
    class UserName(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, LiveMessage.UserName)

            return self.value == other.value

    class Text(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, LiveMessage.Text)

            return self.value == other.value

    def __init__(
            self,
            id_: ID,
            from_user: UserName,
            text: Text,
            sent_at: datetime,
            is_from_bot: bool,
    ):
        self._id = id_
        self._from_user = from_user
        self._text = text
        self._sent_at = sent_at
        self._is_from_bot = is_from_bot

    @property
    def id(self) -> ID:
        return self._id

    @property
    def from_user(self) -> UserName:
        return self._from_user

    @property
    def text(self) -> Text:
        return self._text

    @property
    def sent_at(self) -> datetime:
        return self._sent_at

    @property
    def is_from_bot(self) -> bool:
        return self._is_from_bot

    @classmethod
    def create_user_message(
            cls,
            from_user: UserName,
            text: Text,
            sent_at: datetime,
    ) -> "LiveMessage":
        return cls(
            id_=ID.create(),
            from_user=from_user,
            text=text,
            sent_at=sent_at,
            is_from_bot=False,
        )

    @classmethod
    def create_bot_message(
            cls,
            from_user: UserName,
            text: Text,
            sent_at: datetime,
    ) -> "LiveMessage":
        return cls(
            id_=ID.create(),
            from_user=from_user,
            text=text,
            sent_at=sent_at,
            is_from_bot=True,
        )


class LiveChat(Aggregate):
    class ExternalID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, LiveChat.ExternalID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    def __init__(
            self,
            external_id: ExternalID,
            bot_id: ID,
            recent_messages: list[LiveMessage],
    ):
        super().__init__()
        self._external_id = external_id
        self._bot_id = bot_id
        self._recent_messages = recent_messages

    @property
    def id(self) -> ExternalID:
        return self._external_id

    @property
    def external_id(self) -> ExternalID:
        return self._external_id

    @property
    def bot_id(self) -> ID:
        return self._bot_id

    @property
    def recent_messages(self) -> list[LiveMessage]:
        return self._recent_messages

    @classmethod
    def create(
            cls,
            external_id: ExternalID,
            bot_id: ID,
    ) -> "LiveChat":
        return cls(
            external_id=external_id,
            bot_id=bot_id,
            recent_messages=[],
        )

    def append_message(
            self,
            message: LiveMessage,
    ) -> None:
        self._recent_messages.append(message)

    def count_messages_since_last_bot_reply(self) -> int:
        count: int = 0
        for message in reversed(self._recent_messages):
            if message.is_from_bot:
                break
            count += 1

        return count
