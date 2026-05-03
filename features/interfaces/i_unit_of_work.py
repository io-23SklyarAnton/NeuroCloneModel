__all__ = [
    "IUnitOfWork",
]

import abc
from typing import Self

from features.interfaces import repositories


class IUnitOfWork(abc.ABC):
    chat: repositories.IChatRepository
    thread: repositories.IThreadRepository
    message: repositories.IMessageRepository

    def __enter__(self) -> Self:
        raise NotImplementedError

    def __exit__(self, *args) -> None:
        self.rollback()

    @abc.abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def flush(self) -> None: ...

    @abc.abstractmethod
    def rollback(self) -> None: ...
