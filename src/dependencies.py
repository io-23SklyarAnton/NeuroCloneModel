from dishka import Provider, Scope, provide

from bot_operations.application.features import (
    CreateBotCommandHandler,
    ReceiveChatMessageCommandHandler,
    RunBotCommandHandler,
)
from bot_operations.application.interfaces import (
    IBotRunnerService,
    IUnitOfWork as BotOpsUoW,
    NeuroCloneReader,
    PersonaReplyService,
)
from bot_operations.infrastructure.dummy_bot_runner import DummyBotRunnerService
from bot_operations.infrastructure.in_memory.uow import (
    InMemoryUnitOfWork as BotOpsInMemoryUoW,
)
from constants import BASE_PATH
from iam.application.features import RegisterUserCommandHandler
from iam.application.interfaces import IUnitOfWork as IamUoW
from iam.infrastructure.in_memory.uow import (
    InMemoryUnitOfWork as IamInMemoryUoW,
)
from infrastructure.llm import IInferenceEngine
from ml_pipeline.application.features import (
    CreateChatExportCommandHandler,
    MarkNeuroCloneFailedCommandHandler,
    MarkNeuroCloneReadyCommandHandler,
    RequestNeuroCloneCommandHandler,
)
from ml_pipeline.application.interfaces import (
    IStorage,
    IUnitOfWork as MlPipelineUoW,
)
from ml_pipeline.application.queries import (
    NeuroCloneReader as MLNeuroCloneReader,
)
from ml_pipeline.application.services import (
    PersonaReplyService as MLPersonaReplyService,
)
from ml_pipeline.infrastructure.in_memory.uow import (
    InMemoryUnitOfWork as MlPipelineInMemoryUoW,
)
from ml_pipeline.infrastructure.local.storage import LocalStorage


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def get_bot_runner(self) -> IBotRunnerService:
        return DummyBotRunnerService()

    @provide(scope=Scope.APP)
    def get_storage(self) -> IStorage:
        return LocalStorage(
            base_path=BASE_PATH.parent / "storage",
            bucket_name="chat-exports",
        )

    @provide(scope=Scope.REQUEST)
    def get_iam_uow(self) -> IamUoW:
        return IamInMemoryUoW()

    @provide(scope=Scope.REQUEST)
    def get_bot_ops_uow(self) -> BotOpsUoW:
        return BotOpsInMemoryUoW()

    @provide(scope=Scope.REQUEST)
    def get_ml_pipeline_uow(self) -> MlPipelineUoW:
        return MlPipelineInMemoryUoW()

    @provide(scope=Scope.REQUEST)
    def get_neuroclone_reader(
            self,
            uow: MlPipelineUoW,
    ) -> NeuroCloneReader:
        return MLNeuroCloneReader(uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_persona_reply_service(
            self,
            uow: MlPipelineUoW,
            inference_engine: IInferenceEngine,
    ) -> PersonaReplyService:
        return MLPersonaReplyService(
            uow=uow,
            inference_engine=inference_engine,
        )

    @provide(scope=Scope.REQUEST)
    def get_register_user_handler(
            self,
            uow: IamUoW,
    ) -> RegisterUserCommandHandler:
        return RegisterUserCommandHandler(uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_create_bot_handler(
            self,
            uow: BotOpsUoW,
    ) -> CreateBotCommandHandler:
        return CreateBotCommandHandler(uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_run_bot_handler(
            self,
            uow: BotOpsUoW,
            bot_runner: IBotRunnerService,
            neuroclone_reader: NeuroCloneReader,
    ) -> RunBotCommandHandler:
        return RunBotCommandHandler(
            uow=uow,
            bot_runner=bot_runner,
            neuroclone_reader=neuroclone_reader,
        )

    @provide(scope=Scope.REQUEST)
    def get_receive_chat_message_handler(
            self,
            uow: BotOpsUoW,
            persona_reply_service: PersonaReplyService,
    ) -> ReceiveChatMessageCommandHandler:
        return ReceiveChatMessageCommandHandler(
            uow=uow,
            persona_reply_service=persona_reply_service,
        )

    @provide(scope=Scope.REQUEST)
    def get_create_chat_export_handler(
            self,
            uow: MlPipelineUoW,
            storage: IStorage,
    ) -> CreateChatExportCommandHandler:
        return CreateChatExportCommandHandler(uow=uow, storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_request_neuroclone_handler(
            self,
            uow: MlPipelineUoW,
    ) -> RequestNeuroCloneCommandHandler:
        return RequestNeuroCloneCommandHandler(uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_mark_neuroclone_ready_handler(
            self,
            uow: MlPipelineUoW,
    ) -> MarkNeuroCloneReadyCommandHandler:
        return MarkNeuroCloneReadyCommandHandler(uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_mark_neuroclone_failed_handler(
            self,
            uow: MlPipelineUoW,
    ) -> MarkNeuroCloneFailedCommandHandler:
        return MarkNeuroCloneFailedCommandHandler(uow=uow)
