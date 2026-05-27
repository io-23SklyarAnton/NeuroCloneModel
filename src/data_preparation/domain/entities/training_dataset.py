__all__ = ["TrainingDataset"]

import uuid
from datetime import datetime

from common.domain.entities import Aggregate
from common.domain.value_objects import ID, UserName, ValueObject
from data_preparation.domain.entities.chat_export import ChatExport
from data_preparation.domain.value_objects import DatasetFileKey


class TrainingDataset(Aggregate):
    class OwnerTelegramID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, TrainingDataset.OwnerTelegramID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    class EventDatasetBuilt(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            dataset_id: uuid.UUID
            owner_telegram_id: int
            target_user_name: str
            dataset_file_key: str
            source_chat_export_id: int
            n_pairs: int

    def __init__(
            self,
            id_: ID,
            owner_id: OwnerTelegramID,
            target_user: UserName,
            source_chat_export_ids: list[ChatExport.ChatID],
            file_key: DatasetFileKey,
            n_pairs: int,
            built_at: datetime,
    ):
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._target_user = target_user
        self._source_chat_export_ids = source_chat_export_ids
        self._file_key = file_key
        self._n_pairs = n_pairs
        self._built_at = built_at

    @property
    def id(self) -> ID:
        return self._id

    @property
    def owner_id(self) -> OwnerTelegramID:
        return self._owner_id

    @property
    def target_user(self) -> UserName:
        return self._target_user

    @property
    def source_chat_export_ids(self) -> list[ChatExport.ChatID]:
        return self._source_chat_export_ids

    @property
    def file_key(self) -> DatasetFileKey:
        return self._file_key

    @property
    def n_pairs(self) -> int:
        return self._n_pairs

    @property
    def built_at(self) -> datetime:
        return self._built_at

    @classmethod
    def create(
            cls,
            owner_id: OwnerTelegramID,
            target_user: UserName,
            source_chat_export_ids: list[ChatExport.ChatID],
            file_key: DatasetFileKey,
            n_pairs: int,
            built_at: datetime,
    ) -> "TrainingDataset":
        dataset: "TrainingDataset" = cls(
            id_=ID.create(),
            owner_id=owner_id,
            target_user=target_user,
            source_chat_export_ids=source_chat_export_ids,
            file_key=file_key,
            n_pairs=n_pairs,
            built_at=built_at,
        )
        primary_chat_export_id: int = (
            source_chat_export_ids[0].value if source_chat_export_ids else 0
        )
        dataset._events_to_publish.append(cls.EventDatasetBuilt(
            object_id=str(dataset.id.value),
            payload=cls.EventDatasetBuilt.Payload(
                dataset_id=dataset.id.value,
                owner_telegram_id=owner_id.value,
                target_user_name=target_user.value,
                dataset_file_key=file_key.value,
                source_chat_export_id=primary_chat_export_id,
                n_pairs=n_pairs,
            ),
        ))
        return dataset
