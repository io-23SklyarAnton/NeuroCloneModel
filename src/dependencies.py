from typing import Iterable

from dishka import Provider, Scope, provide
from sqlalchemy.orm import sessionmaker

from bot_operations.application.features import (
    AssignNeuroCloneToBotCommandHandler,
    CreateBotCommandHandler,
    ReceiveChatMessageCommandHandler,
    RunBotCommandHandler,
)
from bot_operations.application.interfaces import (
    IBotRunnerService,
    IUnitOfWork as BotOpsUoW,
    PersonaReplyService,
)
from bot_operations.infrastructure.db import (
    SqlAlchemyUnitOfWork as BotOpsSqlAlchemyUoW,
)
from bot_operations.infrastructure.dummy_bot_runner import DummyBotRunnerService
from common.application.interfaces import IEventBus
from common.infrastructure.db.utils import get_session_maker
from constants import BASE_PATH
from data_preparation.application.features import (
    BuildImitationDatasetCommandHandler,
    CreateChatExportCommandHandler,
    IngestChatExportCommandHandler,
    ProcessChatThreadsCommandHandler,
)
from data_preparation.application.interfaces import (
    IStorage,
    IUnitOfWork as DataPrepUoW,
)
from data_preparation.infrastructure.db import (
    SqlAlchemyUnitOfWork as DataPrepSqlAlchemyUoW,
)
from data_preparation.infrastructure.local.storage import LocalStorage
from iam.application.features import RegisterUserCommandHandler
from iam.application.interfaces import IUnitOfWork as IamUoW
from iam.infrastructure.db import SqlAlchemyUnitOfWork as IamSqlAlchemyUoW
from infrastructure.celery.event_bus import CeleryEventBus
from infrastructure.llm import IInferenceEngine
from model_engine.application.features import (
    CreateNeuroCloneCommandHandler,
    TrainLoraAdapterCommandHandler,
)
from model_engine.application.interfaces import (
    IUnitOfWork as ModelEngineUoW,
)
from model_engine.application.services import (
    PersonaInferenceService,
)
from model_engine.infrastructure.db import (
    SqlAlchemyUnitOfWork as ModelEngineSqlAlchemyUoW,
)


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def get_session_maker(self) -> sessionmaker:
        return get_session_maker()

    @provide(scope=Scope.APP)
    def get_event_bus(self) -> IEventBus:
        return CeleryEventBus()

    @provide(scope=Scope.APP)
    def get_bot_runner(self) -> IBotRunnerService:
        return DummyBotRunnerService()

    @provide(scope=Scope.APP)
    def get_storage(self) -> IStorage:
        return LocalStorage(
            base_path=BASE_PATH.parent / "storage",
        )

    @provide(scope=Scope.REQUEST)
    def get_iam_uow(self, session_maker: sessionmaker) -> Iterable[IamUoW]:
        with IamSqlAlchemyUoW(session_factory=session_maker) as uow:
            yield uow

    @provide(scope=Scope.REQUEST)
    def get_bot_ops_uow(self, session_maker: sessionmaker) -> Iterable[BotOpsUoW]:
        with BotOpsSqlAlchemyUoW(session_factory=session_maker) as uow:
            yield uow

    @provide(scope=Scope.REQUEST)
    def get_data_prep_uow(self, session_maker: sessionmaker) -> Iterable[DataPrepUoW]:
        with DataPrepSqlAlchemyUoW(session_factory=session_maker) as uow:
            yield uow

    @provide(scope=Scope.REQUEST)
    def get_model_engine_uow(self, session_maker: sessionmaker) -> Iterable[ModelEngineUoW]:
        with ModelEngineSqlAlchemyUoW(session_factory=session_maker) as uow:
            yield uow

    @provide(scope=Scope.REQUEST)
    def get_persona_reply_service(
            self,
            uow: ModelEngineUoW,
            inference_engine: IInferenceEngine,
    ) -> PersonaReplyService:
        return PersonaInferenceService(
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
    ) -> RunBotCommandHandler:
        return RunBotCommandHandler(
            uow=uow,
            bot_runner=bot_runner,
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
    def get_assign_neuroclone_to_bot_handler(
            self,
            uow: BotOpsUoW,
    ) -> AssignNeuroCloneToBotCommandHandler:
        return AssignNeuroCloneToBotCommandHandler(uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_create_chat_export_handler(
            self,
            uow: DataPrepUoW,
            storage: IStorage,
    ) -> CreateChatExportCommandHandler:
        return CreateChatExportCommandHandler(uow=uow, storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_ingest_chat_export_handler(
            self,
            uow: DataPrepUoW,
            storage: IStorage,
    ) -> IngestChatExportCommandHandler:
        return IngestChatExportCommandHandler(uow=uow, storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_process_chat_threads_handler(
            self,
            uow: DataPrepUoW,
            inference_engine: IInferenceEngine,
    ) -> ProcessChatThreadsCommandHandler:
        return ProcessChatThreadsCommandHandler(
            uow=uow,
            inference_engine=inference_engine,
        )

    @provide(scope=Scope.REQUEST)
    def get_build_imitation_dataset_handler(
            self,
            uow: DataPrepUoW,
            storage: IStorage,
    ) -> BuildImitationDatasetCommandHandler:
        return BuildImitationDatasetCommandHandler(uow=uow, storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_create_neuroclone_handler(
            self,
            uow: ModelEngineUoW,
    ) -> CreateNeuroCloneCommandHandler:
        return CreateNeuroCloneCommandHandler(uow=uow)

    @provide(scope=Scope.REQUEST)
    def get_train_lora_adapter_handler(
            self,
            uow: ModelEngineUoW,
            inference_engine: IInferenceEngine,
    ) -> TrainLoraAdapterCommandHandler:
        return TrainLoraAdapterCommandHandler(
            uow=uow,
            inference_engine=inference_engine,
        )
