__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import json
from io import BytesIO
from typing import Optional

import pydantic

from common.application.base import ICommand, Response
from ml_pipeline.application.interfaces import IStorage, IUnitOfWork
from ml_pipeline.domain.entities import ChatExport
from ml_pipeline.domain.value_objects import ExportFileKey


class Command(ICommand):
    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    owner_id: ChatExport.OwnerTelegramID
    file_bytes: BytesIO


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
            return Response(message="Invalid chat export file.")

        existing: Optional[ChatExport] = await self._uow.chat_export.get_by_id_optional(chat_id)
        if existing is not None:
            return Response(message="Chat export with this chat id already exists.")

        export_file_key = self._build_export_file_key(chat_id)

        await self._storage.save(
            file_object=command.file_bytes,
            file_name=str(export_file_key),
        )

        chat_export = ChatExport.create(
            chat_id=chat_id,
            owner_id=command.owner_id,
            export_file_key=export_file_key,
        )
        self._uow.chat_export.create(chat_export)
        await self._uow.commit()

        return Response(message=f"Chat export {chat_id.value} is now {chat_export.status.value}.")

    def _get_chat_id_from_file(
            self,
            file_bytes: BytesIO,
    ) -> Optional[ChatExport.ChatID]:
        try:
            file_content = file_bytes.read().decode("utf-8")
            data = json.loads(file_content)
            file_bytes.seek(0)
            return ChatExport.ChatID(value=int(data["id"]))
        except Exception:
            return None

    def _build_export_file_key(
            self,
            chat_id: ChatExport.ChatID,
    ) -> ExportFileKey:
        return ExportFileKey(value=f"chat-exports/{chat_id.value}.json")
