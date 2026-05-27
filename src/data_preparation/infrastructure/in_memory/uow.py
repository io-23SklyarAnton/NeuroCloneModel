__all__ = ["InMemoryUnitOfWork"]

from common.domain.entities import Aggregate
from data_preparation.application.interfaces import IUnitOfWork
from data_preparation.infrastructure.in_memory import repositories


class InMemoryUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self._outbox: list[Aggregate.IDomainEvent] = []
        self.chat_export = repositories.InMemoryChatExportRepository({})
        self.parsed_message = repositories.InMemoryParsedMessageRepository({})
        self.thread = repositories.InMemoryThreadRepository({})
        self.training_dataset = repositories.InMemoryTrainingDatasetRepository(
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
