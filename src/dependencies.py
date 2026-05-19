from dishka import Provider, Scope, provide
from infrastructure.in_memory.uow import InMemoryUnitOfWork
from features import RegisterUserCommandHandler


class AppProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> None:
        return None

    @provide(scope=Scope.REQUEST)
    def get_uow(self) -> InMemoryUnitOfWork:
        return InMemoryUnitOfWork()

    @provide(scope=Scope.REQUEST)
    def get_register_handler(
            self,
            uow: InMemoryUnitOfWork,
    ) -> RegisterUserCommandHandler:
        return RegisterUserCommandHandler(uow=uow)
