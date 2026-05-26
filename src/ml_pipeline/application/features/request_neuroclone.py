__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import uuid
from typing import Optional

import pydantic

from common.application.base import ICommand
from common.domain.value_objects import UserName
from ml_pipeline.application.interfaces import IUnitOfWork
from ml_pipeline.domain.entities import ChatExport, NeuroClone


class Command(ICommand):
    owner_id: NeuroClone.OwnerTelegramID
    target_user_name: UserName
    source_chat_export_id: ChatExport.ChatID


class Response(pydantic.BaseModel):
    neuroclone_id: Optional[uuid.UUID]
    message: str


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def handle(
            self,
            command: Command,
    ) -> Response:
        chat_export: Optional[ChatExport] = await self._uow.chat_export.get_by_id_optional(
            command.source_chat_export_id,
        )
        if chat_export is None:
            return Response(
                neuroclone_id=None,
                message=f"Chat export {command.source_chat_export_id.value} not found.",
            )

        neuroclone: NeuroClone = NeuroClone.request(
            owner_id=command.owner_id,
            target_user_name=command.target_user_name,
            source_chat_export_id=command.source_chat_export_id,
        )
        self._uow.neuroclone.create(neuroclone)
        await self._uow.commit()

        return Response(
            neuroclone_id=neuroclone.id.value,
            message=(
                f"NeuroClone {neuroclone.id.value} is now {neuroclone.status.value}; "
                f"training will start asynchronously."
            ),
        )
