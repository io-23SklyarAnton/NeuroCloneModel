__all__ = [
    "SqlAlchemyUnitOfWork",
]

from typing import Callable, Self

from sqlalchemy.orm import Session

from ml_pipeline.application.interfaces import IUnitOfWork
from ml_pipeline.infrastructure.db import repositories


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(
            self,
            session_factory: Callable[[], Session],
    ) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session: Session = self._session_factory()
        self.chat_export = repositories.ChatExportRepository(self._session)
        self.parsed_message = repositories.ParsedMessageRepository(self._session)
        self.thread = repositories.ThreadRepository(self._session)
        self.training_dataset = repositories.TrainingDatasetRepository(self._session)
        self.neuroclone = repositories.NeuroCloneRepository(self._session)

        return self

    def __exit__(self, *args) -> None:
        self._session.close()

    async def commit(self) -> None:
        self._session.commit()

    async def flush(self) -> None:
        self._session.flush()

    async def rollback(self) -> None:
        self._session.rollback()
