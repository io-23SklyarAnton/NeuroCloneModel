__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import random
from typing import Optional

import pydantic

from bot_operations.application import constants
from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot, LiveChat, LiveMessage
from common.application.base import ICommand
from common.domain.value_objects import ID
from common.exceptions.base import UnexpectedError
from ml_pipeline.application.interfaces import IInferenceEngine
from utils import get_now_datetime


class Command(ICommand):
    bot_id: ID
    chat_external_id: LiveChat.ExternalID
    user_name: LiveMessage.UserName
    text: LiveMessage.Text


class Response(pydantic.BaseModel):
    reply_text: Optional[str]


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            inference_engine: IInferenceEngine,
            reply_probability_threshold: float,
    ) -> None:
        self._uow = uow
        self._inference_engine = inference_engine
        self._reply_probability_threshold = reply_probability_threshold

    async def handle(
            self,
            command: Command,
    ) -> Response:
        live_chat: LiveChat = await self._get_or_create_chat(
            external_id=command.chat_external_id,
            bot_id=command.bot_id,
        )

        incoming_message: LiveMessage = LiveMessage.create(
            from_user=command.user_name,
            text=command.text,
            sent_at=get_now_datetime(),
        )
        live_chat.append_message(incoming_message)
        self._uow.live_chat.update(live_chat)

        if not self._should_reply():
            await self._uow.commit()
            return Response(reply_text=None)

        bot: Bot = await self._uow.bot.get_by_id_or_raise(command.bot_id)

        generated_text: str = await self._generate_reply(
            bot=bot,
            live_chat=live_chat,
            target_user_name=command.user_name,
        )

        bot_message: LiveMessage = LiveMessage.create(
            from_user=LiveMessage.UserName(value=bot.name.value),
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

    def _should_reply(self) -> bool:
        return random.random() < self._reply_probability_threshold

    async def _generate_reply(
            self,
            bot: Bot,
            live_chat: LiveChat,
            target_user_name: LiveMessage.UserName,
    ) -> str:
        user_prompt: str = self._build_user_prompt(live_chat)
        lora_path: Optional[str] = bot.lora_path.value

        if lora_path is None:
            raise UnexpectedError("Bot is not trained yet")

        return await self._inference_engine.generate_async(
            system_prompt=constants.REPLY_SYSTEM_PROMPT.format(target_user_name.value),  # TODO: avoid duplicating this constant in ml_pipeline
            user_prompt=user_prompt,
            lora_path=lora_path,
            max_tokens=constants.REPLY_MAX_TOKENS,
            temp=constants.REPLY_TEMP,
            priority=constants.REPLY_PRIORITY,
        )

    @staticmethod
    def _build_user_prompt(
            live_chat: LiveChat,
    ) -> str:
        recent_messages: list[LiveMessage] = (
            live_chat.recent_messages[-constants.REPLY_CONTEXT_MESSAGES_LIMIT:]
        )
        lines: list[str] = [  # TODO: use jinja template for this
            f"{message.from_user.value}: {message.text.value}"
            for message in recent_messages
        ]
        return "\n".join(lines)
