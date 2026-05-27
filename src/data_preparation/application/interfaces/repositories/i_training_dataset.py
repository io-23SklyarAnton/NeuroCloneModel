__all__ = ["ITrainingDatasetRepository"]

import abc
from typing import Optional

from common.domain.value_objects import ID, OwnerTelegramID
from common.infrastructure.db.i_base_repository import IBaseRepository
from data_preparation.domain.entities import TrainingDataset


class ITrainingDatasetRepository(IBaseRepository[TrainingDataset]):
    @abc.abstractmethod
    async def get_by_id_or_raise(
            self,
            dataset_id: ID,
    ) -> TrainingDataset: ...

    @abc.abstractmethod
    async def get_by_id_optional(
            self,
            dataset_id: ID,
    ) -> Optional[TrainingDataset]: ...

    @abc.abstractmethod
    async def get_by_owner_id(
            self,
            owner_id: OwnerTelegramID,
    ) -> list[TrainingDataset]: ...
