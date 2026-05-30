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
    force_reply: bool = False


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

        existing_chat: Optional[LiveChat] = await self._uow.live_chat.get_by_id_optional(
            command.chat_external_id,
        )
        is_new_chat: bool = existing_chat is None
        live_chat: LiveChat = existing_chat if existing_chat is not None else LiveChat.create(
            external_id=command.chat_external_id,
            bot_id=command.bot_id,
        )

        incoming_message: LiveMessage = LiveMessage.create_user_message(
            from_user=command.user_name,
            text=command.text,
            sent_at=get_now_datetime(),
        )
        live_chat.append_message(incoming_message)

        reply_text: Optional[str] = await self._maybe_generate_reply(
            bot=bot,
            live_chat=live_chat,
            force_reply=command.force_reply,
        )
        if reply_text is not None:
            bot_message: LiveMessage = LiveMessage.create_bot_message(
                from_user=UserName(value=bot.name.value),
                text=LiveMessage.Text(value=reply_text),
                sent_at=get_now_datetime(),
            )
            live_chat.append_message(bot_message)

        if is_new_chat:
            self._uow.live_chat.create(live_chat)
        else:
            self._uow.live_chat.update(live_chat)

        await self._uow.commit()

        return Response(reply_text=reply_text)

    async def _maybe_generate_reply(
            self,
            bot: Bot,
            live_chat: LiveChat,
            force_reply: bool,
    ) -> Optional[str]:
        if bot.neuroclone_id is None:
            return None

        if not self._should_reply(
                reply_period=bot.reply_period,
                live_chat=live_chat,
                force_reply=force_reply,
        ):
            return None

        return await self._persona_reply_service.generate_reply(
            neuroclone_id=bot.neuroclone_id.value,
            context=[
                ChatContextMessage(
                    sender=message.from_user.value,
                    text=message.text.value,
                )
                for message in live_chat.recent_messages
            ],
        )

    @staticmethod
    def _should_reply(
            reply_period: Optional[ReplyPeriod],
            live_chat: LiveChat,
            force_reply: bool,
    ) -> bool:
        if force_reply:
            return True

        if reply_period is None:
            return False

        messages_since_last_reply: int = live_chat.count_messages_since_last_bot_reply()
        if messages_since_last_reply == 0:
            return False

        geometric_trial_probability: float = 1.0 / reply_period.value
        return random.random() < geometric_trial_probability
