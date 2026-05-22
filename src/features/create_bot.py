__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

from io import BytesIO
from typing import Optional
import json

from domain.entities import User, Bot, Chat, ChatExport
from domain.value_objects import ExportFileKey
from features import interfaces
from features.base import ICommand, Response
import constants


class Command(ICommand):
    requester_telegram_id: User.TelegramID
    bot_name: Bot.Name
    bot_token: Bot.Token
    file_bytes: BytesIO


class CommandHandler:
    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
            storage: interfaces.IStorage,
    ) -> None:
        self._uow = uow
        self._storage = storage

    async def handle(
            self,
            command: Command,
    ) -> Response:
        requester: Optional[User] = await self._uow.user.get_by_id_optional(command.requester_telegram_id)
        if requester is None:
            return Response(message="You need to register first by sending /start.")

        bot: Optional[Bot] = await self._uow.bot.get_by_token_optional(command.bot_token)
        if bot is not None:
            return Response(message="Bot with this token already exists.")

        user_bots = await self._uow.bot.get_by_owner_id(requester.id)
        if len(user_bots) >= constants.USER_BOT_LIMIT:
            return Response(message=f"You have reached the maximum number of bots ({constants.USER_BOT_LIMIT}).")

        chat_id: Optional[Chat.ExternalID] = self._get_chat_id_from_file(command.file_bytes)
        if chat_id is None:
            return Response(message="Invalid chat export file.")

        chat_export_file_key = self._get_chat_export_file_key(chat_id)

        await self._storage.save(
            file_object=command.file_bytes,
            file_name=str(chat_export_file_key),
        )

        chat_export = ChatExport.create(
            chat_id=chat_id,
            owner_id=requester.id,
            export_file_key=chat_export_file_key,
        )

        bot = Bot.create(
            name=command.bot_name,
            token=command.bot_token,
            owner_id=requester.id,
            chat_exports=[chat_export],
        )
        self._uow.bot.create(bot)
        await self._uow.commit()

        return Response(message=f"Bot «{bot.name.value}» is now {bot.status.value}.")

    def _get_chat_id_from_file(
            self,
            file_bytes: BytesIO,
    ) -> Optional[Chat.ExternalID]:
        try:
            file_content = file_bytes.read().decode("utf-8")
            data = json.loads(file_content)
            file_bytes.seek(0)
            return data["id"]
        except Exception:
            return None

    def _get_chat_export_file_key(
            self,
            chat_id: Chat.ExternalID,
    ) -> ExportFileKey:
        return ExportFileKey(value=f"chat-exports/{chat_id}.json")
