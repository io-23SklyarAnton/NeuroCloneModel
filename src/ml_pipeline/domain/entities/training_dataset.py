__all__ = ["TrainingDataset"]

from datetime import datetime

from common.domain.entities import Aggregate
from common.domain.value_objects import ID, ValueObject, UserName
from ml_pipeline.domain.entities.chat_export import ChatExport
from ml_pipeline.domain.value_objects import DatasetFileKey


class TrainingDataset(Aggregate):
    class OwnerTelegramID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, TrainingDataset.OwnerTelegramID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

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
        return cls(
            id_=ID.create(),
            owner_id=owner_id,
            target_user=target_user,
            source_chat_export_ids=source_chat_export_ids,
            file_key=file_key,
            n_pairs=n_pairs,
            built_at=built_at,
        )
