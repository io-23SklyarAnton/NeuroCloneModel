__all__ = ["NeuroClone"]

import uuid
from enum import StrEnum
from typing import Optional

from common.domain.entities import Aggregate
from common.domain.value_objects import ID, UserName, ValueObject, OwnerTelegramID


class NeuroClone(Aggregate):
    class Status(StrEnum):
        PREPARING = "PREPARING"
        TRAINING = "TRAINING"
        READY = "READY"
        FAILED = "FAILED"

    class DatasetFileKey(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, NeuroClone.DatasetFileKey)

            return self.value == other.value

        def __str__(self) -> str:
            return self.value

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

    class EventNeuroCloneReady(Aggregate.IDomainEvent):
        ...

    class EventNeuroCloneFailed(Aggregate.IDomainEvent):
        ...

    def __init__(
            self,
            id_: ID,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            dataset_file_key: Optional[DatasetFileKey],
            status: Status,
            adapter_path: Optional[AdapterPath],
    ) -> None:
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._target_user_name = target_user_name
        self._dataset_file_key = dataset_file_key
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
    def dataset_file_key(self) -> Optional[DatasetFileKey]:
        return self._dataset_file_key

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
    def create(
            cls,
            owner_id: OwnerTelegramID,
            target_user_name: UserName,
            dataset_file_key: DatasetFileKey,
    ) -> "NeuroClone":
        return NeuroClone(
            id_=ID(value=uuid.uuid4()),
            owner_id=owner_id,
            target_user_name=target_user_name,
            dataset_file_key=dataset_file_key,
            status=cls.Status.PREPARING,
            adapter_path=None,
        )

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
        ))

    def mark_failed(self) -> None:
        self._status = self.Status.FAILED

        self._events_to_publish.append(NeuroClone.EventNeuroCloneFailed(
            object_id=str(self._id.value),
        ))
