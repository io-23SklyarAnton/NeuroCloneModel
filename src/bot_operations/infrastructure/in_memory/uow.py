__all__ = ["InMemoryUnitOfWork"]

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.infrastructure.in_memory import repositories


class InMemoryUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self.bot = repositories.InMemoryBotRepository({})
        self.live_chat = repositories.InMemoryLiveChatRepository({})

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
