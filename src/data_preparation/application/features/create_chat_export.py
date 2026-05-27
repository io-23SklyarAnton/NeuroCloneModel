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
from data_preparation.application.interfaces import IStorage, IUnitOfWork
from data_preparation.domain.entities import ChatExport
from data_preparation.domain.value_objects import ExportFileKey


class Command(ICommand):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    owner_id: ChatExport.OwnerTelegramID
    file_bytes: BytesIO


class Response(pydantic.BaseModel):
    chat_export_id: Optional[int]
    chat_export_file_key: Optional[str]
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
                chat_export_file_key=None,
                message="Invalid chat export file.",
            )

        existing: Optional[ChatExport] = await self._uow.chat_export.get_by_id_optional(chat_id)
        if existing is not None:
            return Response(
                chat_export_id=existing.chat_id.value,
                chat_export_file_key=existing.export_file_key.value,
                message="Chat export with this chat id already exists.",
            )

        export_file_key: ExportFileKey = self._build_export_file_key(chat_id)

        await self._storage.save(
            file_object=command.file_bytes,
            file_name=str(export_file_key),
        )

        chat_export: ChatExport = ChatExport.create(
            chat_id=chat_id,
            owner_id=command.owner_id,
            export_file_key=export_file_key,
        )
        self._uow.chat_export.create(chat_export)
        await self._uow.commit()

        return Response(
            chat_export_id=chat_id.value,
            chat_export_file_key=export_file_key.value,
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

    def _build_export_file_key(
            self,
            chat_id: ChatExport.ChatID,
    ) -> ExportFileKey:
        return ExportFileKey(value=f"chat-exports/{chat_id.value}.json")
