__all__ = ["InMemoryUnitOfWork"]

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.infrastructure.in_memory import repositories
from common.domain.entities import Aggregate


class InMemoryUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self._outbox: list[Aggregate.IDomainEvent] = []
        self.bot = repositories.InMemoryBotRepository({}, outbox=self._outbox)
        self.live_chat = repositories.InMemoryLiveChatRepository({}, outbox=self._outbox)

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
