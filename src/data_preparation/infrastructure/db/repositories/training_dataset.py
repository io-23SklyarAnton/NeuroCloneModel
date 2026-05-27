__all__ = [
    "TrainingDatasetRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from common.domain.value_objects import ID, UserName, OwnerTelegramID
from common.exceptions.base import UnexpectedError
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository
from data_preparation.application.interfaces.repositories import ITrainingDatasetRepository
from data_preparation.domain.entities import ChatExport, TrainingDataset as TrainingDatasetAggregate
from data_preparation.domain.value_objects import DatasetFileKey
from data_preparation.infrastructure.db.models import TrainingDataset as DBTrainingDataset


class TrainingDatasetRepository(
    ITrainingDatasetRepository,
    BaseRepository[TrainingDatasetAggregate, DBTrainingDataset],
):
    @property
    def model(self) -> type[DBTrainingDataset]:
        return DBTrainingDataset

    async def get_by_id_or_raise(
            self,
            dataset_id: ID,
    ) -> TrainingDatasetAggregate:
        dataset: Optional[TrainingDatasetAggregate] = await self.get_by_id_optional(dataset_id)
        if dataset is None:
            raise UnexpectedError(f"TrainingDataset with id={dataset_id.value} not found")

        return dataset

    async def get_by_id_optional(
            self,
            dataset_id: ID,
    ) -> Optional[TrainingDatasetAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_id(query, dataset_id)

        db_dataset: Optional[DBTrainingDataset] = query.first()
        return self.get_optional(db_dataset)

    async def get_by_owner_id(
            self,
            owner_id: TrainingDatasetAggregate.OwnerTelegramID,
    ) -> list[TrainingDatasetAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_owner_id(query, owner_id)

        db_datasets: list[DBTrainingDataset] = query.all()
        return self.get_all(db_datasets)

    def from_aggregate_to_db_model(
            self,
            aggregate: TrainingDatasetAggregate,
    ) -> DBTrainingDataset:
        return DBTrainingDataset(
            id=aggregate.id.value,
            owner_telegram_id=aggregate.owner_id.value,
            target_user=aggregate.target_user.value,
            source_chat_export_id=aggregate.source_chat_export_id.value,
            file_key=aggregate.file_key.value,
            n_pairs=aggregate.n_pairs,
            built_at=aggregate.built_at.replace(tzinfo=None),
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBTrainingDataset,
    ) -> TrainingDatasetAggregate:
        return TrainingDatasetAggregate(
            id_=ID(value=db_model.id),
            owner_id=OwnerTelegramID(value=db_model.owner_telegram_id),
            target_user=UserName(value=db_model.target_user),
            source_chat_export_id=ChatExport.ChatID(value=db_model.source_chat_export_id),
            file_key=DatasetFileKey(value=db_model.file_key),
            n_pairs=db_model.n_pairs,
            built_at=db_model.built_at,
        )

    def _filter_by_id(
            self,
            query: Query,
            dataset_id: ID,
    ) -> Query:
        return query.filter(self.model.id == dataset_id.value)

    def _filter_by_owner_id(
            self,
            query: Query,
            owner_id: OwnerTelegramID,
    ) -> Query:
        return query.filter(self.model.owner_telegram_id == owner_id.value)
