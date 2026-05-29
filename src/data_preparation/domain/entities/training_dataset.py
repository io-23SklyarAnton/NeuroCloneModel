__all__ = ["TrainingDataset"]

from datetime import datetime

from common.domain.entities import Aggregate
from common.domain.value_objects import (
    FileReference,
    ID,
    OwnerTelegramID,
    ReplyPeriod,
    UserName,
)
from data_preparation.domain.entities.chat_export import ChatExport


class TrainingDataset(Aggregate):
    class EventDatasetBuilt(Aggregate.IDomainEvent):
        class Payload(Aggregate.IDomainEvent.Payload):
            owner_telegram_id: int
            target_user_name: str
            file_reference: FileReference
            source_chat_export_id: int
            n_pairs: int
            reply_period: int

        payload: Payload

    def __init__(
            self,
            id_: ID,
            owner_id: OwnerTelegramID,
            target_user: UserName,
            source_chat_export_id: ChatExport.ChatID,
            file_reference: FileReference,
            n_pairs: int,
            built_at: datetime,
            reply_period: ReplyPeriod,
    ):
        super().__init__()
        self._id = id_
        self._owner_id = owner_id
        self._target_user = target_user
        self._source_chat_export_id = source_chat_export_id
        self._file_reference = file_reference
        self._n_pairs = n_pairs
        self._built_at = built_at
        self._reply_period = reply_period

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
    def source_chat_export_id(self) -> ChatExport.ChatID:
        return self._source_chat_export_id

    @property
    def file_reference(self) -> FileReference:
        return self._file_reference

    @property
    def n_pairs(self) -> int:
        return self._n_pairs

    @property
    def built_at(self) -> datetime:
        return self._built_at

    @property
    def reply_period(self) -> ReplyPeriod:
        return self._reply_period

    @classmethod
    def create(
            cls,
            owner_id: OwnerTelegramID,
            target_user: UserName,
            source_chat_export_id: ChatExport.ChatID,
            file_reference: FileReference,
            n_pairs: int,
            built_at: datetime,
            reply_period: ReplyPeriod,
    ) -> "TrainingDataset":
        dataset: "TrainingDataset" = cls(
            id_=ID.create(),
            owner_id=owner_id,
            target_user=target_user,
            source_chat_export_id=source_chat_export_id,
            file_reference=file_reference,
            n_pairs=n_pairs,
            built_at=built_at,
            reply_period=reply_period,
        )
        dataset._events_to_publish.append(cls.EventDatasetBuilt(
            object_id=str(dataset.id.value),
            payload=cls.EventDatasetBuilt.Payload(
                owner_telegram_id=owner_id.value,
                target_user_name=target_user.value,
                file_reference=file_reference,
                source_chat_export_id=source_chat_export_id.value,
                n_pairs=n_pairs,
                reply_period=reply_period.value,
            ),
        ))
        return dataset
