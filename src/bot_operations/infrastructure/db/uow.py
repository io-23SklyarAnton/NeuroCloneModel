__all__ = [
    "SqlAlchemyUnitOfWork",
]

from typing import Callable, Self

from sqlalchemy.orm import Session

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.infrastructure.db import repositories


class SqlAlchemyUnitOfWork(IUnitOfWork):
    def __init__(
            self,
            session_factory: Callable[[], Session],
    ) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> Self:
        self._session: Session = self._session_factory()
        self.bot = repositories.BotRepository(self._session)
        self.live_chat = repositories.LiveChatRepository(self._session)

        return self

    def __exit__(self, *args) -> None:
        self._session.close()

    async def commit(self) -> None:
        self._session.commit()

    async def flush(self) -> None:
        self._session.flush()

    async def rollback(self) -> None:
        self._session.rollback()
