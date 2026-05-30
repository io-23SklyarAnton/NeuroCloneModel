__all__ = ["create_router"]

import asyncio
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

CHARS_PER_SECOND = 15.0
MIN_TYPING_DELAY = 0.5
MAX_TYPING_DELAY = 4.0


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

        await _send_split_response(message, response.reply_text)

    return router


async def _send_split_response(
        message: Message,
        full_reply_text: str,
) -> None:
    parts = full_reply_text.split("\n")

    for part in parts:
        clean_part = part.strip()

        if not clean_part:
            continue

        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )

        calculated_delay = len(clean_part) / CHARS_PER_SECOND
        typing_delay = max(MIN_TYPING_DELAY, min(calculated_delay, MAX_TYPING_DELAY))

        await asyncio.sleep(typing_delay)
        await message.answer(clean_part)
