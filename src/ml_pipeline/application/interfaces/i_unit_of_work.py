__all__ = ["IUnitOfWork"]

import abc
from typing import Self

from ml_pipeline.application.interfaces import repositories


class IUnitOfWork(abc.ABC):
    chat_export: repositories.IChatExportRepository
    thread: repositories.IThreadRepository
    training_dataset: repositories.ITrainingDatasetRepository

    def __enter__(self) -> Self:
        raise NotImplementedError

    def __exit__(self, *args) -> None:
        self.rollback()

    @abc.abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def flush(self) -> None: ...

    @abc.abstractmethod
    async def rollback(self) -> None: ...
