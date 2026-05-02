import datetime
from typing import Optional
import pydantic
from typing_extensions import Self

import jinja2

import constants
from domain.entities import Thread
from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.value_objects import ID, DateUnixtime
from features import interfaces
from features.base import ICommand
from llm import IInferenceEngine


class Command(ICommand):
    chat_id: Chat.ExternalID


class CommandHandler:
    class ThreadDecision(pydantic.BaseModel):
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
        thread_decision: Optional["CommandHandler.ThreadDecision"]

        @pydantic.model_validator(mode='after')
        def validate_error_and_decision(self) -> Self:
            if self.error_message is not None:
                assert self.thread_decision is None
            else:
                assert self.thread_decision is not None

    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
            inference_engine: IInferenceEngine,
    ):
        self._uow = uow
        self._inference_engine = inference_engine
        self._active_threads: dict[ID, Thread] = {}

        self._jinja_env = jinja2.Environment(autoescape=False)
        self._disentanglement_template = self._jinja_env.from_string(constants.DIALOGUE_DISENTANGLEMENT_TEMPLATE)
        self._thread_summary_template = self._jinja_env.from_string(constants.THREAD_SUMMARY_TEMPLATE)

    async def handle(self, command: Command) -> None:
        chat: Chat = await self._get_chat_by_id(command.chat_id)

        for offset in range(0, chat.n_messages, constants.BATCH_SIZE_DIALOGUE_DISENTANGLEMENT):
            await self._process_batch(
                chat_id=command.chat_id,
                offset=offset,
            )

    async def _process_batch(
            self,
            chat_id: Chat.ExternalID,
            offset: int,
    ) -> None:
        messages: list[Message] = await self._get_batch_of_messages(
            chat_id=chat_id,
            offset=offset,
            limit=constants.BATCH_SIZE_DIALOGUE_DISENTANGLEMENT,
        )
        messages_sub: list[Message] = await self._get_batch_of_messages(
            chat_id=chat_id,
            offset=offset + 1,
            limit=constants.W_SUB + constants.BATCH_SIZE_DIALOGUE_DISENTANGLEMENT,
        )

        for i, message in enumerate(messages, 1):
            await self._process_single_message(
                i=i,
                message=message,
                messages_sub=messages_sub,
                chat_id=chat_id,
            )

    async def _process_single_message(
            self,
            i: int,
            message: Message,
            messages_sub: list[Message],
            chat_id: Chat.ExternalID,
    ) -> None:
        determined_thread: Optional[Thread] = await self._determine_message_thread(
            i=i,
            message=message,
            messages_sub=messages_sub,
            chat_id=chat_id,
        )

        if determined_thread is not None:
            determined_thread.add_message(message)
            if determined_thread.needs_summary_update():
                new_summary = await self._generate_thread_summary(determined_thread)
                determined_thread.update_summary(new_summary)

        self._remove_outdated_threads(message.sequence_number)

    async def _determine_message_thread(
            self,
            i: int,
            message: Message,
            messages_sub: list[Message],
            chat_id: Chat.ExternalID,
    ) -> Optional[Thread]:
        if message.has_reply_message_id():
            thread: Optional[Thread] = await self._determine_replied_message_thread(
                message=message,
                chat_id=chat_id,
            )
            if thread is not None:
                return thread

        return await self._determine_non_replied_message_thread(
            i=i,
            message=message,
            messages_sub=messages_sub,
        )

    async def _generate_thread_summary(
            self,
            thread: Thread,
    ) -> Thread.Summary:
        recent_messages = thread.recent_messages[-constants.N_LAST_MESSAGES_FOR_SUMMARY:]

        messages_data = [
            {
                "sender": message.from_user.value,
                "text": message.text.value,
            }
            for message in recent_messages
        ]

        prompt: str = self._thread_summary_template.render(
            previous_summary=getattr(thread.summary.value, 'value', None),
            messages=messages_data,
        )

        raw_summary: str = await self._inference_engine.generate_async(
            prompt=prompt,
            lora_path=None,
            max_tokens=constants.MAX_TOKENS_THREAD_SUMMARY,
            temp=constants.TEMP_THREAD_SUMMARY,
        )

        return Thread.Summary(value=raw_summary.strip())

    async def _determine_replied_message_thread(
            self,
            message: Message,
            chat_id: Chat.ExternalID,
    ) -> Optional[Thread]:
        thread: Optional[Thread] = self._get_thread_from_active_threads_by_message_external_id(
            message_external_id=message.external_id,
        )
        if thread is None:
            thread = await self._get_thread_by_message_external_id_and_chat_id(
                message_external_id=message.external_id,
                chat_id=chat_id,
            )

            if thread is None:
                return None

            self._add_thread_to_active(thread)

        return thread

    async def _determine_non_replied_message_thread(
            self,
            i: int,
            message: Message,
            messages_sub: list[Message],
    ) -> Thread:
        clipped_messages_sub: list[Message] = self._clip_messages_sub(
            messages_sub=messages_sub,
            i=i,
        )
        thread_mapping: dict[int, ID] = self._generate_thread_mapping()

        decision: "CommandHandler.ThreadDecision" = await self._get_thread_decision_with_retries(
            message=message,
            clipped_messages_sub=clipped_messages_sub,
            thread_mapping=thread_mapping,
        )

        return self._apply_thread_decision(
            decision=decision,
            message=message,
        )

    async def _get_thread_decision_with_retries(
            self,
            message: Message,
            clipped_messages_sub: list[Message],
            thread_mapping: dict[int, ID],
    ) -> "CommandHandler.ThreadDecision":
        warning_message: str = ""

        for _ in range(constants.N_ATTEMPTS):
            prompt: str = self._get_prompt(
                message=message,
                clipped_messages_sub=clipped_messages_sub,
                warning_message=warning_message,
                thread_mapping=thread_mapping,
            )
            raw_thread_decision: str = await self._get_decision(prompt)

            parsed_thread_decision: "CommandHandler.ParsedThreadDecision" = self._parse_thread_decision(
                raw_thread_decision=raw_thread_decision,
                thread_mapping=thread_mapping,
            )

            if parsed_thread_decision.error_message is not None:
                warning_message += f"{parsed_thread_decision.error_message}\n"
                continue

            return parsed_thread_decision.thread_decision

        return self.ThreadDecision(
            thread_id=None,
            is_new_thread=True,
        )

    def _apply_thread_decision(
            self,
            decision: "CommandHandler.ThreadDecision",
            message: Message,
    ) -> Thread:
        if decision.is_new_thread:
            new_thread: Thread = self._create_thread(message)
            self._add_thread_to_active(new_thread)
            return new_thread

        return self._get_thread_from_active_threads_by_id(
            thread_id=decision.thread_id,
        )

    async def _get_chat_by_id(
            self,
            chat_id: Chat.ExternalID,
    ) -> Chat:
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

    def _add_thread_to_active(
            self,
            thread: Thread,
    ) -> None:
        self._active_threads[thread.id] = thread

    def _clip_messages_sub(
            self,
            messages_sub: list[Message],
            i: int,
    ) -> list[Message]:
        start_idx = i - 1
        end_idx = start_idx + constants.W_SUB
        return messages_sub[start_idx:end_idx]

    def _generate_thread_mapping(self) -> dict[int, ID]:
        return {
            idx: thread_id for idx, thread_id in enumerate(self._active_threads.keys(), 1)
        }

    def _get_prompt(
            self,
            message: Message,
            clipped_messages_sub: list[Message],
            warning_message: Optional[str],
            thread_mapping: dict[int, ID],
    ) -> str:
        return self._disentanglement_template.render(
            active_threads=self._format_active_threads(thread_mapping),
            target_message=self._format_target_message(message),
            future_messages=self._format_future_messages(
                messages_sub=clipped_messages_sub,
                start_unix=message.date_unixtime,
            ),
            warning_message=warning_message,
        )

    async def _get_decision(
            self,
            prompt: str,
    ) -> str:
        return await self._inference_engine.generate_async(
            prompt=prompt,
            lora_path=None,
            max_tokens=constants.MAX_TOKENS_THREAD_DECISION,
            temp=constants.TEMP_THREAD_DECISION,
        )

    def _parse_thread_decision(
            self,
            raw_thread_decision: str,
            thread_mapping: dict[int, ID],
    ) -> "CommandHandler.ParsedThreadDecision":
        short_id: Optional[int] = self._extract_short_id(
            raw_thread_decision=raw_thread_decision,
        )

        if short_id is None:
            return self.ParsedThreadDecision(
                error_message=f"Invalid output format. Expected integer, got: '{raw_thread_decision}'",
                thread_decision=None,
            )

        if short_id == 0:
            return self.ParsedThreadDecision(
                error_message=None,
                thread_decision=self.ThreadDecision(
                    thread_id=None,
                    is_new_thread=True,
                ),
            )

        real_id: Optional[ID] = thread_mapping.get(short_id)
        if real_id is None:
            return self.ParsedThreadDecision(
                error_message=f"Invalid Thread ID: {short_id}. Must be 0 or one of {list(thread_mapping.keys())}",
                thread_decision=None,
            )

        return self.ParsedThreadDecision(
            error_message=None,
            thread_decision=self.ThreadDecision(
                thread_id=real_id,
                is_new_thread=False,
            ),
        )

    def _extract_short_id(
            self,
            raw_thread_decision: str,
    ) -> Optional[int]:
        cleaned_output = raw_thread_decision.strip().strip('.')
        try:
            return int(cleaned_output)
        except ValueError:
            return None

    def _format_active_threads(
            self,
            thread_mapping: dict[int, ID],
    ) -> list[dict]:
        active_threads_data = []
        reverse_mapping = {v: k for k, v in thread_mapping.items()}

        for thread in self._active_threads.values():
            short_id = reverse_mapping[thread.id]
            active_threads_data.append(self._format_thread(
                thread=thread,
                short_id=short_id,
            ))

        return active_threads_data

    def _format_thread(
            self,
            thread: Thread,
            short_id: int,
    ) -> dict:
        recent_messages = thread.recent_messages[-constants.N_LAST_MESSAGES_IN_THREAD:]
        last_timestamp = self._format_timestamp(recent_messages[-1].date_unixtime)

        return {
            "id": short_id,
            "summary": thread.summary.value,
            "last_timestamp": last_timestamp,
            "messages": self._format_thread_messages(messages=recent_messages),
        }

    def _format_thread_messages(
            self,
            messages: list[Message],
    ) -> list[dict]:
        thread_messages_data = []
        previous_unix = None

        for message in messages:
            thread_messages_data.append({
                "time_display": self._get_time_display(
                    current_unix=message.date_unixtime,
                    previous_unix=previous_unix,
                ),
                "sender": message.from_user.value,
                "text": message.text.value,
            })
            previous_unix = message.date_unixtime

        return thread_messages_data

    def _format_target_message(
            self,
            message: Message,
    ) -> dict:
        return {
            "time_display": self._format_timestamp(message.date_unixtime),
            "sender": message.from_user.value,
            "text": message.text.value,
        }

    def _format_future_messages(
            self,
            messages_sub: list[Message],
            start_unix: DateUnixtime,
    ) -> list[dict]:
        future_messages_data = []
        previous_unix = start_unix
        for message in messages_sub:
            future_messages_data.append({
                "time_display": self._get_time_display(
                    current_unix=message.date_unixtime,
                    previous_unix=previous_unix,
                ),
                "sender": message.from_user.value,
                "text": message.text.value,
            })
            previous_unix = message.date_unixtime

        return future_messages_data

    def _create_thread(
            self,
            message: Message,
    ) -> Thread:
        return Thread.create(message=message)

    def _get_thread_from_active_threads_by_id(
            self,
            thread_id: ID,
    ) -> Optional[Thread]:
        thread = self._active_threads.get(thread_id)
        if thread is not None:
            return thread

        raise ValueError(f"Thread with id {thread_id} not found in active threads")

    def _get_thread_from_active_threads_by_message_external_id(
            self,
            message_external_id: Message.ExternalID,
    ) -> Optional[Thread]:
        for thread in self._active_threads.values():
            for message in thread.recent_messages:
                if message.external_id == message_external_id:
                    return thread

            for message in thread.uncommitted_messages:
                if message.external_id == message_external_id:
                    return thread

        return None

    def _remove_outdated_threads(
            self,
            current_seq_num: Message.SequenceNumber,
    ) -> None:
        self._remove_stale_threads(current_seq_num)
        self._enforce_active_threads_limit()

    def _remove_stale_threads(
            self,
            current_seq_num: Message.SequenceNumber,
    ) -> None:
        for thread in list(self._active_threads.values()):
            last_message_seq_num: Message.SequenceNumber = thread.recent_messages[-1].sequence_number
            if current_seq_num.value - last_message_seq_num.value >= constants.W_PREV:
                del self._active_threads[thread.id]

    def _enforce_active_threads_limit(self) -> None:
        if len(self._active_threads) <= constants.N_ACTIVE_THREADS:
            return

        sorted_threads = sorted(
            self._active_threads.values(),
            key=lambda t: t.recent_messages[-1].sequence_number.value,
            reverse=True,
        )
        for thread in sorted_threads[constants.N_ACTIVE_THREADS:]:
            del self._active_threads[thread.id]

    @classmethod
    def _get_time_display(
            cls,
            current_unix: DateUnixtime,
            previous_unix: Optional[DateUnixtime],
    ) -> str:
        base_str = cls._format_timestamp(current_unix)

        if previous_unix is None:
            return base_str

        delta_str = cls._calculate_time_delta(
            current_unix=current_unix,
            previous_unix=previous_unix,
        )
        return f"{base_str} | {delta_str}"

    @staticmethod
    def _format_timestamp(unix_time: DateUnixtime) -> str:
        return datetime.datetime.fromtimestamp(unix_time.value).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _calculate_time_delta(
            current_unix: DateUnixtime,
            previous_unix: DateUnixtime,
    ) -> str:
        delta_seconds = current_unix.value - previous_unix.value
        if delta_seconds <= 0:
            return "+0s"
        if delta_seconds < 60:
            return f"+{delta_seconds}s"
        if delta_seconds < 3600:
            return f"+{delta_seconds // 60}m"
        if delta_seconds < 86400:
            return f"+{delta_seconds // 3600}h"
        return f"+{delta_seconds // 86400}d"
