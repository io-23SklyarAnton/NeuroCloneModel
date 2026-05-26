__all__ = ["NeuroClone"]

import uuid
from enum import StrEnum
from typing import Optional

from common.domain.entities import Aggregate
from common.domain.value_objects import ID, UserName, ValueObject
from ml_pipeline.domain.entities.chat_export import ChatExport


class NeuroClone(Aggregate):
    class Status(StrEnum):
        PREPARING = "PREPARING"
        TRAINING = "TRAINING"
        READY = "READY"
        FAILED = "FAILED"

    class OwnerTelegramID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, NeuroClone.OwnerTelegramID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    class AdapterPath(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, NeuroClone.AdapterPath)

            return self.value == other.value

        def __str__(self) -> str:
            return self.value

    class IllegalStateTransitionError(RuntimeError):
        def __init__(
                self,
                current: "NeuroClone.Status",
                requested: "NeuroClone.Status",
        ) -> None:
            super().__init__(
                f"Illegal neuroclone status transition: {current.value} -> {requested.value}",
            )

    class EventNeuroCloneRequested(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            neuroclone_id: uuid.UUID
            owner_telegram_id: int
            target_user_name: str
            source_chat_export_id: int

    class EventNeuroCloneReady(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            neuroclone_id: uuid.UUID
            adapter_path: str

    class EventNeuroCloneFailed(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            neuroclone_id: uuid.UUID
            reason: str

    def __init__(
            self,
            id_: ID,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            source_chat_export_id: ChatExport.ChatID,
            status: Status,
            adapter_path: Optional[AdapterPath],
    ) -> None:
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._target_user_name = target_user_name
        self._source_chat_export_id = source_chat_export_id
        self._status = status
        self._adapter_path = adapter_path

    @property
    def id(self) -> ID:
        return self._id

    @property
    def owner_id(self) -> OwnerTelegramID:
        return self._owner_id

    @property
    def target_user_name(self) -> UserName:
        return self._target_user_name

    @property
    def source_chat_export_id(self) -> ChatExport.ChatID:
        return self._source_chat_export_id

    @property
    def status(self) -> Status:
        return self._status

    @property
    def adapter_path(self) -> Optional[AdapterPath]:
        return self._adapter_path

    @property
    def is_ready(self) -> bool:
        return self._status == self.Status.READY

    @classmethod
    def request(
            cls,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            source_chat_export_id: ChatExport.ChatID,
    ) -> "NeuroClone":
        neuroclone: "NeuroClone" = cls(
            id_=ID.create(),
            owner_id=owner_id,
            target_user_name=target_user_name,
            source_chat_export_id=source_chat_export_id,
            status=cls.Status.PREPARING,
            adapter_path=None,
        )
        neuroclone._events_to_publish.append(cls.EventNeuroCloneRequested(
            object_id=str(neuroclone.id.value),
            payload=cls.EventNeuroCloneRequested.Payload(
                neuroclone_id=neuroclone.id.value,
                owner_telegram_id=owner_id.value,
                target_user_name=target_user_name.value,
                source_chat_export_id=source_chat_export_id.value,
            ),
        ))
        return neuroclone

    def start_training(self) -> None:
        if self._status != self.Status.PREPARING:
            raise NeuroClone.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.TRAINING,
            )

        self._status = self.Status.TRAINING

    def mark_ready(
            self,
            adapter_path: AdapterPath,
    ) -> None:
        if self._status not in {self.Status.PREPARING, self.Status.TRAINING}:
            raise NeuroClone.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.READY,
            )

        self._status = self.Status.READY
        self._adapter_path = adapter_path

        self._events_to_publish.append(NeuroClone.EventNeuroCloneReady(
            object_id=str(self._id.value),
            payload=NeuroClone.EventNeuroCloneReady.Payload(
                neuroclone_id=self._id.value,
                adapter_path=adapter_path.value,
            ),
        ))

    def mark_failed(
            self,
            reason: str,
    ) -> None:
        self._status = self.Status.FAILED

        self._events_to_publish.append(NeuroClone.EventNeuroCloneFailed(
            object_id=str(self._id.value),
            payload=NeuroClone.EventNeuroCloneFailed.Payload(
                neuroclone_id=self._id.value,
                reason=reason,
            ),
        ))
