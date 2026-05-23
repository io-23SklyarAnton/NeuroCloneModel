__all__ = ["InMemoryUnitOfWork"]

from ml_pipeline.application.interfaces import IUnitOfWork
from ml_pipeline.infrastructure.in_memory import repositories


class InMemoryUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self.chat_export = repositories.InMemoryChatExportRepository({})
        self.thread = repositories.InMemoryThreadRepository(
            chat_export_repository=self.chat_export,
            storage={},
        )
        self.training_dataset = repositories.InMemoryTrainingDatasetRepository({})

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
