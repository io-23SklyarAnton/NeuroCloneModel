__all__ = ["InMemoryUnitOfWork"]

from iam.application.interfaces import IUnitOfWork
from iam.infrastructure.in_memory import repositories


class InMemoryUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self.user = repositories.InMemoryUserRepository({})

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
