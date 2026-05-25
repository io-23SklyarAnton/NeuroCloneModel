__all__ = ["Bot"]

from enum import StrEnum
from typing import Optional, Self

from pydantic import model_validator

from common.domain.entities import Aggregate
from common.domain.value_objects import ID, ValueObject


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

    class OwnerTelegramID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Bot.OwnerTelegramID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    class LinkedDatasetID(ValueObject):
        value: ID

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Bot.LinkedDatasetID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    class LoraPath(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Bot.LoraPath)

            return self.value == other.value

        def __str__(self) -> str:
            return self.value

    class ReplyPeriod(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Bot.ReplyPeriod)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

        @model_validator(mode='after')
        def validate_value(self) -> Self:
            if self.value < 1:
                raise ValueError("Reply period must be at least 1.")

            return self

    class IllegalStateTransitionError(RuntimeError):
        def __init__(
                self,
                current: "Bot.BotStatus",
                requested: "Bot.BotStatus",
        ) -> None:
            super().__init__(f"Illegal bot status transition: {current.value} -> {requested.value}")

    class NotOwnedError(RuntimeError):
        def __init__(
                self,
                bot_id: ID,
                requester_id: "Bot.OwnerTelegramID",
        ) -> None:
            super().__init__(f"User {requester_id.value} is not the owner of bot {bot_id}")

    def __init__(
            self,
            id_: ID,
            owner_id: OwnerTelegramID,
            token: Token,
            name: Name,
            status: BotStatus,
            linked_dataset_ids: list[LinkedDatasetID],
            lora_path: Optional[LoraPath],
            reply_period: Optional[ReplyPeriod],
    ) -> None:
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._token = token
        self._name = name
        self._status = status
        self._linked_dataset_ids = linked_dataset_ids
        self._lora_path = lora_path
        self._reply_period = reply_period

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
    def linked_dataset_ids(self) -> list[LinkedDatasetID]:
        return self._linked_dataset_ids

    @property
    def lora_path(self) -> Optional[LoraPath]:
        return self._lora_path

    @property
    def reply_period(self) -> Optional[ReplyPeriod]:
        return self._reply_period

    @property
    def is_running(self) -> bool:
        return self._status == self.BotStatus.RUNNING

    @classmethod
    def create(
            cls,
            owner_id: OwnerTelegramID,
            token: Token,
            name: Name,
            linked_dataset_ids: list[LinkedDatasetID],
    ) -> "Bot":
        bot = cls(
            id_=ID.create(),
            owner_id=owner_id,
            token=token,
            name=name,
            status=cls.BotStatus.PENDING,
            linked_dataset_ids=linked_dataset_ids,
            lora_path=None,
            reply_period=None,
        )
        return bot

    def ensure_owned_by(
            self,
            user_id: OwnerTelegramID,
    ) -> None:
        if not (self._owner_id == user_id):
            raise Bot.NotOwnedError(bot_id=self._id, requester_id=user_id)

    def link_dataset(
            self,
            dataset_id: LinkedDatasetID,
    ) -> None:
        if dataset_id in self._linked_dataset_ids:
            return

        self._linked_dataset_ids.append(dataset_id)

    def attach_lora(
            self,
            lora_path: LoraPath,
    ) -> None:
        self._lora_path = lora_path

    def detach_lora(self) -> None:
        self._lora_path = None

    def set_reply_period(
            self,
            reply_period: ReplyPeriod,
    ) -> None:
        self._reply_period = reply_period

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
