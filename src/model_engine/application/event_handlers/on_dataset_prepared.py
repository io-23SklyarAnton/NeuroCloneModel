__all__ = [
    "ITrainingScheduler",
    "OnDatasetPreparedHandler",
]

from typing import Protocol

from common.domain.value_objects import ID, UserName
from contracts.integration_events import DatasetPreparedEvent
from model_engine.application.interfaces import IUnitOfWork
from model_engine.domain.entities import NeuroClone


class ITrainingScheduler(Protocol):
    async def schedule(
            self,
            neuroclone_id: ID,
    ) -> None: ...


class OnDatasetPreparedHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            training_scheduler: ITrainingScheduler,
    ) -> None:
        self._uow = uow
        self._training_scheduler = training_scheduler

    async def handle(
            self,
            event: DatasetPreparedEvent,
    ) -> None:
        neuroclone: NeuroClone = NeuroClone.request(
            owner_id=NeuroClone.OwnerTelegramID(value=event.owner_telegram_id),
            target_user_name=UserName(value=event.target_user_name),
            dataset_file_key=NeuroClone.DatasetFileKey(value=event.dataset_file_key),
        )
        self._uow.neuroclone.create(neuroclone)
        await self._uow.commit()

        await self._training_scheduler.schedule(neuroclone_id=neuroclone.id)
