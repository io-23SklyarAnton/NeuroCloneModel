__all__ = ["Bot"]

import uuid
from enum import StrEnum
from typing import Optional

from common.domain.entities import Aggregate
from common.domain.value_objects import ID, ValueObject, OwnerTelegramID


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
                requested: "Bot.BotStatus",
        ) -> None:
            super().__init__(f"Illegal bot status transition: {current.value} -> {requested.value}")

    class NeuroCloneNotReadyError(RuntimeError):
        def __init__(
                self,
                bot_id: ID,
        ) -> None:
            super().__init__(f"Bot {bot_id} cannot start: its neuroclone is not ready yet.")

    class NotOwnedError(RuntimeError):
        def __init__(
                self,
                bot_id: ID,
                requester_id: OwnerTelegramID,
        ) -> None:
            super().__init__(f"User {requester_id.value} is not the owner of bot {bot_id}")

    class EventBotCreated(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            bot_id: uuid.UUID
            owner_telegram_id: int
            bot_name: str

    class NeuroCloneAssigned(Aggregate.IDomainEvent):
        ...

    def __init__(
            self,
            id_: ID,
            owner_id: OwnerTelegramID,
            token: Token,
            name: Name,
            status: BotStatus,
            neuroclone_id: Optional[ID],
    ) -> None:
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._token = token
        self._name = name
        self._status = status
        self._neuroclone_id = neuroclone_id

    @property
    def id(self) -> ID:
        return self._id

    @property
    def owner_id(self) -> OwnerTelegramID:
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
    def neuroclone_id(self) -> Optional[ID]:
        return self._neuroclone_id

    @property
    def is_running(self) -> bool:
        return self._status == self.BotStatus.RUNNING

    @classmethod
    def create(
            cls,
            owner_id: OwnerTelegramID,
            token: Token,
            name: Name,
    ) -> "Bot":
        bot: "Bot" = cls(
            id_=ID.create(),
            owner_id=owner_id,
            token=token,
            name=name,
            status=cls.BotStatus.PENDING,
            neuroclone_id=None,
        )
        bot._events_to_publish.append(cls.EventBotCreated(
            object_id=str(bot.id.value),
            payload=cls.EventBotCreated.Payload(
                bot_id=bot.id.value,
                owner_telegram_id=owner_id.value,
                bot_name=name.value,
            ),
        ))
        return bot

    def ensure_owned_by(
            self,
            user_id: OwnerTelegramID,
    ) -> None:
        if not (self._owner_id == user_id):
            raise Bot.NotOwnedError(bot_id=self._id, requester_id=user_id)

    def assign_neuroclone(
            self,
            neuroclone_id: ID,
    ) -> None:
        if self._neuroclone_id is not None:
            raise RuntimeError(f"Bot {self._id} already has a neuroclone assigned.")
        self._neuroclone_id = neuroclone_id

        self._events_to_publish.append(Bot.NeuroCloneAssigned(
            object_id=str(self._id.value),
        ))

    def start_bot(self) -> None:
        if self._neuroclone_id is None:
            raise Bot.NeuroCloneNotReadyError(bot_id=self._id)
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
