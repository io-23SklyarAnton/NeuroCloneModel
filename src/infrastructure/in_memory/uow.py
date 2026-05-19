from features.interfaces import IUnitOfWork
from infrastructure.in_memory import repositories


class InMemoryUnitOfWork(IUnitOfWork):
    def __init__(self) -> None:
        self.chat = repositories.InMemoryChatRepository({})
        self.message = repositories.InMemoryMessageRepository({})
        self.thread = repositories.InMemoryThreadRepository(
            messages_storage={},
            storage={},
        )
        self.user = repositories.InMemoryUserRepository({})

    def __enter__(self) -> "InMemoryUnitOfWork":
        return self

    def __exit__(self, *args) -> None:
        self.rollback()

    def commit(self) -> None:
        pass

    def flush(self) -> None:
        pass

    def rollback(self) -> None:
        pass
