__all__ = ["create_router"]

import asyncio
from typing import Optional

from aiogram import F, Router
from aiogram.enums import ChatType, MessageEntityType
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

        force_reply: bool = await _should_force_reply(message)

        response = await command_handler.handle(
            ReceiveChatMessageCommand(
                bot_id=domain_bot_id,
                chat_external_id=LiveChat.ExternalID(value=message.chat.id),
                user_name=UserName(value=user_name_value),
                text=LiveMessage.Text(value=text),
                force_reply=force_reply,
            ),
        )

        if response.reply_text is None:
            return

        await _send_split_response(message, response.reply_text)

    return router


async def _should_force_reply(message: Message) -> bool:
    if message.chat.type == ChatType.PRIVATE:
        return True

    if await _is_bot_mentioned(message):
        return True

    return await _is_reply_to_bot(message)


async def _is_reply_to_bot(message: Message) -> bool:
    reply_to: Optional[Message] = message.reply_to_message
    if reply_to is None or reply_to.from_user is None:
        return False

    bot_user = await message.bot.me()
    return reply_to.from_user.id == bot_user.id


async def _is_bot_mentioned(message: Message) -> bool:
    entities = message.entities or []
    if not entities:
        return False

    bot_user = await message.bot.me()
    bot_id: int = bot_user.id
    bot_username: Optional[str] = bot_user.username
    text: str = message.text or ""

    for entity in entities:
        if entity.type == MessageEntityType.MENTION and bot_username:
            mention_text: str = text[entity.offset: entity.offset + entity.length]
            if mention_text.lower() == f"@{bot_username}".lower():
                return True
        elif entity.type == MessageEntityType.TEXT_MENTION:
            if entity.user is not None and entity.user.id == bot_id:
                return True

    return False


async def _send_split_response(
        message: Message,
        full_reply_text: str,
) -> None:
    parts: list[str] = [p.strip() for p in full_reply_text.split("\n") if p.strip()]

    for idx, clean_part in enumerate(parts):
        await message.bot.send_chat_action(
            chat_id=message.chat.id,
            action="typing"
        )

        calculated_delay = len(clean_part) / CHARS_PER_SECOND
        typing_delay = max(MIN_TYPING_DELAY, min(calculated_delay, MAX_TYPING_DELAY))

        await asyncio.sleep(typing_delay)

        if idx == 0:
            await message.reply(clean_part)
        else:
            await message.answer(clean_part)
