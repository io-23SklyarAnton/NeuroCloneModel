__all__ = ["NeuroClone"]

import uuid
from enum import StrEnum
from typing import Optional

from common.domain.entities import Aggregate
from common.domain.value_objects import (
    FileReference,
    ID,
    OwnerTelegramID,
    ReplyPeriod,
    UserName,
)


class NeuroClone(Aggregate):
    class Status(StrEnum):
        PREPARING = "PREPARING"
        TRAINING = "TRAINING"
        READY = "READY"
        FAILED = "FAILED"

    class IllegalStateTransitionError(RuntimeError):
        def __init__(
                self,
                current: "NeuroClone.Status",
                requested: "NeuroClone.Status",
        ) -> None:
            super().__init__(
                f"Illegal neuroclone status transition: {current.value} -> {requested.value}",
            )

    class EventNeuroCloneCreated(Aggregate.IDomainEvent):
        ...

    class EventNeuroCloneReady(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            owner_telegram_id: OwnerTelegramID
            reply_period: int

        payload: Payload

    class EventNeuroCloneFailed(Aggregate.IDomainEvent):
        ...

    def __init__(
            self,
            id_: ID,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            dataset_file_reference: FileReference,
            status: Status,
            adapter_file_reference: Optional[FileReference],
            reply_period: ReplyPeriod,
    ) -> None:
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._target_user_name = target_user_name
        self._dataset_file_reference = dataset_file_reference
        self._status = status
        self._adapter_file_reference = adapter_file_reference
        self._reply_period = reply_period

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
    def dataset_file_reference(self) -> FileReference:
        return self._dataset_file_reference

    @property
    def status(self) -> Status:
        return self._status

    @property
    def adapter_file_reference(self) -> Optional[FileReference]:
        return self._adapter_file_reference

    @property
    def reply_period(self) -> ReplyPeriod:
        return self._reply_period

    @property
    def is_ready(self) -> bool:
        return self._status == self.Status.READY

    @classmethod
    def create(
            cls,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            dataset_file_reference: FileReference,
            reply_period: ReplyPeriod,
    ) -> "NeuroClone":
        neuroclone = NeuroClone(
            id_=ID(value=uuid.uuid4()),
            owner_id=owner_id,
            target_user_name=target_user_name,
            dataset_file_reference=dataset_file_reference,
            status=cls.Status.PREPARING,
            adapter_file_reference=None,
            reply_period=reply_period,
        )

        neuroclone._events_to_publish.append(NeuroClone.EventNeuroCloneCreated(
            object_id=str(neuroclone.id.value),
        ))
        return neuroclone

    def start_training(self) -> None:
        if self._status != self.Status.PREPARING:
            raise NeuroClone.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.TRAINING,
            )

        self._status = self.Status.TRAINING

    def set_adapter_file_reference(
            self,
            adapter_file_reference: FileReference,
    ) -> None:
        if self._status != self.Status.TRAINING:
            raise NeuroClone.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.TRAINING,
            )

        if self._adapter_file_reference is not None:
            raise RuntimeError(
                f"Adapter file reference is already set for NeuroClone {self._id.value}: "
                f"{self._adapter_file_reference.full_path}",
            )
        self._adapter_file_reference = adapter_file_reference

    def mark_ready(self) -> None:
        if self._status not in {self.Status.PREPARING, self.Status.TRAINING}:
            raise NeuroClone.IllegalStateTransitionError(
                current=self._status,
                requested=self.Status.READY,
            )
        self._status = self.Status.READY

        self._events_to_publish.append(NeuroClone.EventNeuroCloneReady(
            object_id=str(self._id.value),
            payload=NeuroClone.EventNeuroCloneReady.Payload(
                owner_telegram_id=self._owner_id,
                reply_period=self._reply_period.value,
            ),
        ))

    def mark_failed(self) -> None:
        self._status = self.Status.FAILED

        self._events_to_publish.append(NeuroClone.EventNeuroCloneFailed(
            object_id=str(self._id.value),
        ))
