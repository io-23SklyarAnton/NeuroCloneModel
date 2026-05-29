__all__ = ["create_router"]

from typing import Optional

from aiogram import F, Router
from aiogram.types import Message
from dishka.integrations.aiogram import FromDishka, inject

from bot_operations.application.features import (
    ReceiveChatMessageCommand,
    ReceiveChatMessageCommandHandler,
)
from bot_operations.domain.entities import LiveChat, LiveMessage
from common.domain.value_objects import ID, UserName
from common.exceptions.client.malformed_request import MissingUserException


def create_router() -> Router:
    router = Router(name="live_message")

    @router.message(F.text)
    @inject
    async def handle_live_message(
            message: Message,
            domain_bot_id: ID,
            command_handler: FromDishka[ReceiveChatMessageCommandHandler],
    ) -> None:
        if message.from_user is None:
            raise MissingUserException()
        if message.from_user.is_bot:
            return

        text: Optional[str] = message.text
        if text is None or not text.strip():
            return

        user_name_value: Optional[str] = (
            message.from_user.username
            or message.from_user.full_name
        )
        if not user_name_value:
            return

        response = await command_handler.handle(
            ReceiveChatMessageCommand(
                bot_id=domain_bot_id,
                chat_external_id=LiveChat.ExternalID(value=message.chat.id),
                user_name=UserName(value=user_name_value),
                text=LiveMessage.Text(value=text),
            ),
        )

        if response.reply_text is None:
            return

        await message.answer(response.reply_text)

    return router
