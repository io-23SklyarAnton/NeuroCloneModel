__all__ = ["InMemoryNeuroCloneRepository"]

from typing import Optional

from common.domain.entities import Aggregate
from common.domain.value_objects import ID
from common.infrastructure.db.in_memory_repository import InMemoryBaseRepository
from ml_pipeline.application.interfaces.repositories import INeuroCloneRepository
from ml_pipeline.domain.entities import NeuroClone


class InMemoryNeuroCloneRepository(
        InMemoryBaseRepository[NeuroClone],
        INeuroCloneRepository,
):
    def __init__(
            self,
            storage: dict[ID, NeuroClone],
            outbox: Optional[list[Aggregate.IDomainEvent]] = None,
    ):
        super().__init__(storage=storage, outbox=outbox)

    async def get_by_id_or_raise(
            self,
            neuroclone_id: ID,
    ) -> NeuroClone:
        return self.get_or_raise(neuroclone_id)

    async def get_by_id_optional(
            self,
            neuroclone_id: ID,
    ) -> Optional[NeuroClone]:
        return self.get_optional(neuroclone_id)

    async def get_by_owner_id(
            self,
            owner_id: NeuroClone.OwnerTelegramID,
    ) -> list[NeuroClone]:
        return [
            neuroclone
            for neuroclone in self._storage.values()
            if neuroclone.owner_id == owner_id
        ]
