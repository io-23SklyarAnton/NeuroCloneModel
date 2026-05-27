__all__ = ["InMemoryUnitOfWork"]

from common.domain.entities import Aggregate
from model_engine.application.interfaces import IUnitOfWork
from model_engine.infrastructure.in_memory import repositories


class InMemoryUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self._outbox: list[Aggregate.IDomainEvent] = []
        self.neuroclone = repositories.InMemoryNeuroCloneRepository(
            storage={},
            outbox=self._outbox,
        )

    def __enter__(self) -> "InMemoryUnitOfWork":
        return self

    def __exit__(self, *args) -> None:
        self.rollback()

    async def commit(self) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    @property
    def outbox(self) -> list[Aggregate.IDomainEvent]:
        return self._outbox
