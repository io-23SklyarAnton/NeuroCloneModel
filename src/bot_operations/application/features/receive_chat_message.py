__all__ = [
    "Command",
    "CommandHandler",
]

from datetime import datetime
from typing import Optional

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import LiveChat, LiveMessage
from common.application.base import ICommand
from common.domain.value_objects import ID


class Command(ICommand):
    chat_external_id: LiveChat.ExternalID
    bot_id: ID
    from_user: LiveMessage.UserName
    text: LiveMessage.Text
    sent_at: datetime


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
        live_chat: LiveChat = await self._get_or_create_chat(
            external_id=command.chat_external_id,
            bot_id=command.bot_id,
        )
        message = LiveMessage.create(
            from_user=command.from_user,
            text=command.text,
            sent_at=command.sent_at,
        )
        live_chat.append_message(message)

        self._uow.live_chat.update(live_chat)
        await self._uow.commit()

    async def _get_or_create_chat(
            self,
            external_id: LiveChat.ExternalID,
            bot_id: ID,
    ) -> LiveChat:
        existing: Optional[LiveChat] = await self._uow.live_chat.get_by_id_optional(external_id)
        if existing is not None:
            return existing

        new_chat = LiveChat.create(
            external_id=external_id,
            bot_id=bot_id,
        )
        self._uow.live_chat.create(new_chat)

        return new_chat
