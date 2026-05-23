__all__ = ["IUnitOfWork"]

import abc
from typing import Self

from iam.application.interfaces import repositories


class IUnitOfWork(abc.ABC):
    user: repositories.IUserRepository

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
