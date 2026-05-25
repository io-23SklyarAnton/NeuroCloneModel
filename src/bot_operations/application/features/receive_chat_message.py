__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import random
from typing import Optional

import jinja2
import pydantic

from bot_operations.application import constants
from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot, LiveChat, LiveMessage
from common.application.base import ICommand
from common.domain.value_objects import ID, UserName
from infrastructure.llm import IInferenceEngine
from utils import get_now_datetime


class Command(ICommand):
    bot_id: ID
    chat_external_id: LiveChat.ExternalID
    text: LiveMessage.Text


class Response(pydantic.BaseModel):
    reply_text: Optional[str]


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
            inference_engine: IInferenceEngine,
    ) -> None:
        self._uow = uow
        self._inference_engine = inference_engine

        loader: jinja2.FileSystemLoader = jinja2.FileSystemLoader(searchpath=str(constants.PROMPTS_DIR))
        env: jinja2.Environment = jinja2.Environment(
            loader=loader,
            autoescape=False,
        )
        self._template: jinja2.Template = env.get_template(constants.REPLY_CONTEXT_TEMPLATE_NAME)

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

        if not self._should_reply(
                bot=bot,
                live_chat=live_chat,
        ):
            await self._uow.commit()
            return Response(reply_text=None)

        if bot.lora_path is None:
            print(f"ERROR: Bot {bot.id.value} is configured to reply, but has no LoRA path set. Skipping reply.")
            return Response(reply_text=None)

        generated_text: str = await self._generate_reply(
            recent_messages=live_chat.recent_messages,
            target_user_name=bot.target_user_name,
            lora_path=bot.lora_path,
        )

        bot_message: LiveMessage = LiveMessage.create_bot_message(
            from_user=bot.target_user_name,
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
            bot: Bot,
            live_chat: LiveChat,
    ) -> bool:
        if bot.reply_period is None:
            print(f"ERROR: Bot {bot.id.value} has no reply period set, but received a message. Skipping reply.")
            return False

        messages_since_last_reply: int = live_chat.count_messages_since_last_bot_reply()
        if messages_since_last_reply == 0:
            return False

        geometric_trial_probability: float = 1.0 / bot.reply_period.value
        return random.random() < geometric_trial_probability

    async def _generate_reply(
            self,
            recent_messages: list[LiveMessage],
            target_user_name: UserName,
            lora_path: Optional[Bot.LoraPath],
    ) -> str:
        user_prompt: str = self._build_user_prompt(recent_messages)
        system_prompt: str = constants.REPLY_SYSTEM_PROMPT.format(
            target_user=target_user_name.value,
        )

        return await self._inference_engine.generate_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            lora_path=lora_path.value,
            max_tokens=constants.REPLY_MAX_TOKENS,
            temp=constants.REPLY_TEMPERATURE,
            priority=constants.REPLY_PRIORITY,
        )

    def _build_user_prompt(
            self,
            messages: list[LiveMessage],
    ) -> str:
        window = messages[-constants.CONTEXT_WINDOW_MESSAGES:]
        messages_data = [
            {
                "sender": msg.from_user.value,
                "text": msg.text.value,
            }
            for msg in window

        ]
        return self._template.render(messages=messages_data)
