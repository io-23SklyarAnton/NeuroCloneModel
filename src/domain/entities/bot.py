__all__ = ["Bot"]

from enum import StrEnum
from typing import TYPE_CHECKING

from domain.entities.base import Aggregate
from domain.value_objects import ID, ValueObject

if TYPE_CHECKING:
    from domain.entities import User, ChatExport


class Bot(Aggregate):
    class BotStatus(StrEnum):
        PENDING = "PENDING"
        RUNNING = "RUNNING"
        STOPPED = "STOPPED"

    class Token(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Bot.Token)

            return self.value == other.value

    class Name(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Bot.Name)

            return self.value == other.value

    class IllegalStateTransitionError(RuntimeError):
        def __init__(
                self,
                current: "Bot.BotStatus",
                requested: "Bot.BotStatus"
        ) -> None:
            super().__init__(f"Illegal bot status transition: {current.value} -> {requested.value}")

    class NotOwnedError(RuntimeError):
        def __init__(
                self,
                bot_id: ID,
                requester_id: "User.TelegramID",
        ) -> None:
            super().__init__(f"User {requester_id} is not the owner of bot {bot_id}")

    class EventBotCreated(Aggregate.IDomainEvent):
        ...

    def __init__(
            self,
            id_: ID,
            owner_id: "User.TelegramID",
            token: Token,
            name: Name,
            status: BotStatus,
            chat_exports: list["ChatExport"],
    ) -> None:
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._token = token
        self._name = name
        self._status = status
        self._chat_exports = chat_exports

    @property
    def id(self) -> ID:
        return self._id

    @property
    def owner_id(self) -> "User.TelegramID":
        return self._owner_id

    @property
    def token(self) -> Token:
        return self._token

    @property
    def name(self) -> Name:
        return self._name

    @property
    def status(self) -> BotStatus:
        return self._status

    @property
    def chat_exports(self) -> list["ChatExport"]:
        return self._chat_exports

    @property
    def is_running(self) -> bool:
        return self._status == self.BotStatus.RUNNING

    @classmethod
    def create(
            cls,
            owner_id: "User.TelegramID",
            token: Token,
            name: Name,
            chat_exports: list["ChatExport"],
    ) -> "Bot":
        bot = cls(
            id_=ID.create(),
            owner_id=owner_id,
            token=token,
            name=name,
            status=cls.BotStatus.PENDING,
            chat_exports=chat_exports,
        )
        bot._events_to_publish.append(cls.EventBotCreated(object_id=str(bot.id.value)))
        return bot

    def ensure_owned_by(
            self,
            user_id: "User.TelegramID",
    ) -> None:
        if not (self._owner_id == user_id):
            raise Bot.NotOwnedError(bot_id=self._id, requester_id=user_id)

    def start_bot(self) -> None:
        if self.is_running:
            raise Bot.IllegalStateTransitionError(
                current=self._status,
                requested=self.BotStatus.RUNNING,
            )

        self._status = self.BotStatus.RUNNING

    def stop_bot(self) -> None:
        if not self.is_running:
            raise Bot.IllegalStateTransitionError(
                current=self._status,
                requested=self.BotStatus.STOPPED,
            )

        self._status = self.BotStatus.STOPPED
