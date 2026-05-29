__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import json
from io import BytesIO
from typing import Optional

import pydantic

from common.application.base import ICommand
from common.application.interfaces import IStorage
from common.domain.value_objects import FileReference, OwnerTelegramID, UserName
from data_preparation.application.interfaces import IUnitOfWork
from data_preparation.domain.entities import ChatExport

_BUCKET_NAME = "chat-exports"


class Command(ICommand):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    owner_id: OwnerTelegramID
    target_user_name: UserName
    file_bytes: BytesIO


class Response(pydantic.BaseModel):
    chat_export_id: Optional[int]
    chat_export_file_path: Optional[str]
    message: str


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            storage: IStorage,
    ) -> None:
        self._uow = uow
        self._storage = storage

    async def handle(
            self,
            command: Command,
    ) -> Response:
        chat_id: Optional[ChatExport.ChatID] = self._get_chat_id_from_file(command.file_bytes)
        if chat_id is None:
            return Response(
                chat_export_id=None,
                chat_export_file_path=None,
                message="Invalid chat export file.",
            )

        existing: Optional[ChatExport] = await self._uow.chat_export.get_by_id_optional(chat_id)
        if existing is not None:
            return Response(
                chat_export_id=existing.chat_id.value,
                chat_export_file_path=existing.file_reference.full_path,
                message="Chat export with this chat id already exists.",
            )

        file_reference: FileReference = self._build_file_reference(chat_id)

        await self._storage.save(
            file_object=command.file_bytes,
            file_reference=file_reference,
        )

        chat_export: ChatExport = ChatExport.create(
            chat_id=chat_id,
            owner_id=command.owner_id,
            target_user_name=command.target_user_name,
            file_reference=file_reference,
        )
        self._uow.chat_export.create(chat_export)
        await self._uow.commit()

        return Response(
            chat_export_id=chat_id.value,
            chat_export_file_path=file_reference.full_path,
            message=f"Chat export {chat_id.value} is now {chat_export.status.value}.",
        )

    def _get_chat_id_from_file(
            self,
            file_bytes: BytesIO,
    ) -> Optional[ChatExport.ChatID]:
        try:
            file_content: str = file_bytes.read().decode("utf-8")
            data: dict = json.loads(file_content)
            file_bytes.seek(0)
            return ChatExport.ChatID(value=int(data["id"]))
        except Exception:
            return None

    @staticmethod
    def _build_file_reference(
            chat_id: ChatExport.ChatID,
    ) -> FileReference:
        return FileReference(
            bucket=_BUCKET_NAME,
            key=f"{chat_id.value}.json",
        )
