from dishka import Provider, Scope, provide

from bot_operations.application.interfaces import IBotRunnerService, IUnitOfWork as BotOpsUoW
from bot_operations.infrastructure.dummy_bot_runner import DummyBotRunnerService
from bot_operations.infrastructure.in_memory.uow import InMemoryUnitOfWork as BotOpsInMemoryUoW
from iam.application.features import RegisterUserCommandHandler
from iam.application.interfaces import IUnitOfWork as IamUoW
from iam.infrastructure.in_memory.uow import InMemoryUnitOfWork as IamInMemoryUoW


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def get_bot_runner(self) -> IBotRunnerService:
        return DummyBotRunnerService()

    @provide(scope=Scope.REQUEST)
    def get_iam_uow(self) -> IamUoW:
        return IamInMemoryUoW()

    @provide(scope=Scope.REQUEST)
    def get_bot_ops_uow(self) -> BotOpsUoW:
        return BotOpsInMemoryUoW()

    @provide(scope=Scope.REQUEST)
    def get_register_user_handler(
            self,
            uow: IamUoW,
    ) -> RegisterUserCommandHandler:
        return RegisterUserCommandHandler(uow=uow)
