__all__ = ["EventHandler"]

from common.application.interfaces import IEventBus
from common.domain.value_objects import OwnerTelegramID, ReplyPeriod, UserName
from data_preparation.domain.entities import TrainingDataset
from model_engine.application.features import create_neuroclone


class EventHandler:
    def __init__(
            self,
            bus: IEventBus,
    ) -> None:
        self._bus = bus

    async def handle(
            self,
            event: TrainingDataset.EventDatasetBuilt,
    ) -> None:
        await self._bus.group_apply([
            create_neuroclone.Command(
                owner_id=OwnerTelegramID(value=event.payload.owner_telegram_id),
                target_user_name=UserName(value=event.payload.target_user_name),
                dataset_file_reference=event.payload.file_reference,
                reply_period=ReplyPeriod(value=event.payload.reply_period),
            ),
        ])
