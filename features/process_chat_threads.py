import datetime
from typing import Optional
import pydantic
from typing_extensions import Self

import jinja2

import constants
from domain.entities import Thread
from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.value_objects import ID
from features import interfaces
from features.base import ICommand


class Command(ICommand):
    chat_id: Chat.ExternalID


class CommandHandler:
    class ThreadDecision(pydantic.BaseModel):
        reason: str
        thread_id: Optional[ID]
        is_new_thread: bool

        @pydantic.model_validator(mode='after')
        def validate_is_new_thread(self) -> Self:
            if self.is_new_thread:
                assert self.thread_id is None
            else:
                assert self.thread_id is not None

    class ParsedThreadDecision(pydantic.BaseModel):
        error_message: Optional[str]
        thread_decision: "CommandHandler.ThreadDecision"

    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
    ):
        self._uow = uow
        self._active_threads: list[Thread] = []

        self._jinja_env = jinja2.Environment(autoescape=False)
        self._template = self._jinja_env.from_string(constants.DIALOGUE_DISENTANGLEMENT_TEMPLATE)

    async def handle(self, command: Command) -> None:
        chat: Chat = await self._get_chat_by_id(command.chat_id)

        for offset in range(0, chat.n_messages, constants.BATCH_SIZE_DIALOGUE_DISENTANGLEMENT):
            messages: list[Message] = await self._get_batch_of_messages(
                chat_id=command.chat_id,
                offset=offset,
                limit=constants.BATCH_SIZE_DIALOGUE_DISENTANGLEMENT,
            )
            messages_sub: list[Message] = await self._get_batch_of_messages(
                chat_id=command.chat_id,
                offset=offset + 1,
                limit=constants.W_SUB + constants.BATCH_SIZE_DIALOGUE_DISENTANGLEMENT,
            )

            for i, message in enumerate(messages, 1):
                determined_thread: Optional[Thread] = await self._determine_message_thread(
                    i,
                    message,
                    messages_sub,
                    command.chat_id,
                )

                if determined_thread is not None:
                    await self._update_active_threads(
                        message,
                        determined_thread
                    )

                await self._remove_outdated_threads(message.sequence_number)

    async def _determine_message_thread(
            self,
            i: int,
            message: Message,
            messages_sub: list[Message],
            chat_id: Chat.ExternalID,
    ):
        if message.has_reply_message_id():
            return await self._determine_replied_message_thread(message, chat_id)
        else:
            return await self._determine_non_replied_message_thread(
                i,
                message,
                messages_sub,
                chat_id
            )

    async def _determine_replied_message_thread(
            self,
            message: Message,
            chat_id: Chat.ExternalID,
    ):
        thread: Optional[Thread] = await self._get_thread_by_message_external_id_and_chat_id(
            message_external_id=message.external_id,
            chat_id=chat_id,
        )

        if thread is None:
            print("WARNING! NO THREAD FOUND")
            return

        self._add_thread_to_active(thread)

        return thread

    async def _determine_non_replied_message_thread(
            self,
            i: int,
            message: Message,
            messages_sub: list[Message],
            chat_id: Chat.ExternalID,
    ):
        clipped_messages_sub: list[Message] = self._clip_messages_sub(
            messages_sub,
            i
        )
        warning_message: str = ""

        for _ in range(constants.N_ATTEMPTS):
            prompt: str = self._get_prompt(
                message,
                clipped_messages_sub,
                warning_message
            )
            raw_thread_decision: str = self._get_decision(prompt)

            parsed_thread_decision: "CommandHandler.ParsedThreadDecision" = self._parse_thread_decision(
                raw_thread_decision,
            )
            if parsed_thread_decision.error_message is not None:
                warning_message += f"{parsed_thread_decision.error_message}\n"
                continue

            if parsed_thread_decision.thread_decision.is_new_thread:
                new_thread: Thread = self._create_thread(message)
                self._add_thread_to_active(new_thread)
                return new_thread
            else:
                return self._get_thread_from_active_threads_by_id(
                    parsed_thread_decision.thread_decision.thread_id
                )

    async def _get_chat_by_id(self, chat_id: ID) -> Chat:
        return await self._uow.chat.get_by_id_or_raise(chat_id)

    async def _get_batch_of_messages(
            self,
            chat_id: Chat.ExternalID,
            offset: int,
            limit: int,
    ) -> list[Message]:
        return await self._uow.message.get_by_chat_id_with_offset_and_limit(
            chat_id=chat_id,
            offset=offset,
            limit=limit,
        )

    async def _get_thread_by_message_external_id_and_chat_id(
            self,
            message_external_id: Message.ExternalID,
            chat_id: Chat.ExternalID,
    ) -> Optional[Thread]:
        return await self._uow.thread.get_by_message_external_id_and_chat_id(
            message_external_id=message_external_id,
            chat_id=chat_id,
        )

    def _add_thread_to_active(self, thread: Thread) -> None:
        self._active_threads.append(thread)

    def _clip_messages_sub(
            self,
            messages_sub: list[Message],
            i: int,
    ) -> list[Message]:
        return messages_sub[i:constants.W_SUB + 1]

    def _get_prompt(
            self,
            message: Message,
            clipped_messages_sub: list[Message],
            warning_message: Optional[str],
    ) -> str:
        active_threads_data = []
        for thread in self._active_threads:
            thread_messages_data = []
            previous_unix = None

            recent_messages = thread.messages[-constants.N_LAST_MESSAGES_IN_THREAD:]

            for message in recent_messages:
                thread_messages_data.append({
                    "time_display": self._get_time_display(
                        current_unix=message.date_unixtime,
                        previous_unix=previous_unix,
                    ),
                    "sender": message.from_user,
                    "text": message.text
                })
                previous_unix = message.date_unixtime

            active_threads_data.append({
                "id": thread.id,
                "summary": thread.summary,
                "last_timestamp": self._get_time_display(recent_messages[-1].date_unixtime, None),
                "messages": thread_messages_data
            })

        target_message_data = {
            "time_display": self._get_time_display(message.date_unixtime, None),
            "sender": message.from_user,
            "text": message.text
        }

        future_messages_data = []
        previous_unix = message.date_unixtime
        for message in clipped_messages_sub:
            future_messages_data.append({
                "time_display": self._get_time_display(message.date_unixtime, previous_unix),
                "sender": message.from_user,
                "text": message.text
            })
            previous_unix = message.date_unixtime

        prompt = self._template.render(
            active_threads=active_threads_data,
            target_message=target_message_data,
            future_messages=future_messages_data,
            warning_message=warning_message,
        )

        return prompt

    @staticmethod
    def _get_time_display(
            current_unix: int,
            previous_unix: Optional[int]
    ) -> str:
        current_dt = datetime.datetime.fromtimestamp(current_unix)
        base_str = current_dt.strftime("%Y-%m-%d %H:%M:%S")

        if previous_unix is None:
            return base_str

        delta_seconds = current_unix - previous_unix
        if delta_seconds <= 0:
            return f"{base_str} | +0s"

        if delta_seconds < 60:
            delta_str = f"+{delta_seconds}s"
        elif delta_seconds < 3600:
            delta_str = f"+{delta_seconds // 60}m"
        elif delta_seconds < 86400:
            delta_str = f"+{delta_seconds // 3600}h"
        else:
            delta_str = f"+{delta_seconds // 86400}d"

        return f"{base_str} | {delta_str}"
