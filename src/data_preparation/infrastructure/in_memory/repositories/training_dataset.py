__all__ = ["InMemoryTrainingDatasetRepository"]

from typing import Optional

from common.domain.entities import Aggregate
from common.domain.value_objects import ID
from common.infrastructure.db.in_memory_repository import InMemoryBaseRepository
from data_preparation.application.interfaces.repositories import ITrainingDatasetRepository
from data_preparation.domain.entities import TrainingDataset


class InMemoryTrainingDatasetRepository(InMemoryBaseRepository[TrainingDataset], ITrainingDatasetRepository):
    def __init__(
            self,
            storage: dict[ID, TrainingDataset],
            outbox: Optional[list[Aggregate.IDomainEvent]] = None,
    ):
        super().__init__(storage=storage, outbox=outbox)

    async def get_by_id_or_raise(
            self,
            dataset_id: ID,
    ) -> TrainingDataset:
        return self.get_or_raise(dataset_id)

    async def get_by_id_optional(
            self,
            dataset_id: ID,
    ) -> Optional[TrainingDataset]:
        return self.get_optional(dataset_id)

    async def get_by_owner_id(
            self,
            owner_id: TrainingDataset.OwnerTelegramID,
    ) -> list[TrainingDataset]:
        return [
            dataset for dataset in self._storage.values()
            if dataset.owner_id == owner_id
        ]
