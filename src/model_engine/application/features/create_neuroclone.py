__all__ = [
    "Command",
    "CommandHandler",
]

from common.application.base import ICommand
from common.domain.value_objects import (
    FileReference,
    OwnerTelegramID,
    ReplyPeriod,
    UserName,
)
from model_engine.application.interfaces import IUnitOfWork
from model_engine.domain.entities import NeuroClone


class Command(ICommand):
    owner_id: OwnerTelegramID
    target_user_name: UserName
    dataset_file_reference: FileReference
    reply_period: ReplyPeriod


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def handle(
            self,
            command: Command,
    ) -> None:
        neuroclone: NeuroClone = NeuroClone.create(
            owner_id=command.owner_id,
            target_user_name=command.target_user_name,
            dataset_file_reference=command.dataset_file_reference,
            reply_period=command.reply_period,
        )

        self._uow.neuroclone.create(neuroclone)
        await self._uow.commit()
