__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import random
from typing import Optional

import pydantic

from bot_operations.application.interfaces import (
    ChatContextMessage,
    IUnitOfWork,
    PersonaReplyService,
)
from bot_operations.domain.entities import Bot, LiveChat, LiveMessage
from common.application.base import ICommand
from common.domain.value_objects import ID, ReplyPeriod, UserName
from utils import get_now_datetime


class Command(ICommand):
    bot_id: ID
    chat_external_id: LiveChat.ExternalID
    user_name: UserName
    text: LiveMessage.Text


class Response(pydantic.BaseModel):
    reply_text: Optional[str]


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            persona_reply_service: PersonaReplyService,
    ) -> None:
        self._uow = uow
        self._persona_reply_service = persona_reply_service

    async def handle(
            self,
            command: Command,
    ) -> Response:
        bot: Bot = await self._uow.bot.get_by_id_or_raise(command.bot_id)

        live_chat: LiveChat = await self._get_or_create_chat(
            external_id=command.chat_external_id,
            bot_id=command.bot_id,
        )

        incoming_message: LiveMessage = LiveMessage.create_user_message(
            from_user=command.user_name,
            text=command.text,
            sent_at=get_now_datetime(),
        )
        live_chat.append_message(incoming_message)
        self._uow.live_chat.update(live_chat)

        if bot.neuroclone_id is None:
            await self._uow.commit()
            return Response(reply_text=None)

        if not self._should_reply(
                reply_period=bot.reply_period,
                live_chat=live_chat,
        ):
            await self._uow.commit()
            return Response(reply_text=None)

        generated_text: Optional[str] = await self._persona_reply_service.generate_reply(
            neuroclone_id=bot.neuroclone_id.value,
            context=[
                ChatContextMessage(
                    sender=message.from_user.value,
                    text=message.text.value,
                )
                for message in live_chat.recent_messages
            ],
        )
        if generated_text is None:
            await self._uow.commit()
            return Response(reply_text=None)

        bot_message: LiveMessage = LiveMessage.create_bot_message(
            from_user=UserName(value=bot.name.value),
            text=LiveMessage.Text(value=generated_text),
            sent_at=get_now_datetime(),
        )
        live_chat.append_message(bot_message)
        self._uow.live_chat.update(live_chat)

        await self._uow.commit()

        return Response(reply_text=generated_text)

    async def _get_or_create_chat(
            self,
            external_id: LiveChat.ExternalID,
            bot_id: ID,
    ) -> LiveChat:
        existing: Optional[LiveChat] = await self._uow.live_chat.get_by_id_optional(external_id)
        if existing is not None:
            return existing

        new_chat: LiveChat = LiveChat.create(
            external_id=external_id,
            bot_id=bot_id,
        )
        self._uow.live_chat.create(new_chat)

        return new_chat

    @staticmethod
    def _should_reply(
            reply_period: Optional[ReplyPeriod],
            live_chat: LiveChat,
    ) -> bool:
        if reply_period is None:
            return False

        messages_since_last_reply: int = live_chat.count_messages_since_last_bot_reply()
        if messages_since_last_reply == 0:
            return False

        geometric_trial_probability: float = 1.0 / reply_period.value
        return random.random() < geometric_trial_probability
