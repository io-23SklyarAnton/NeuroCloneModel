__all__ = [
    "Command",
    "CommandHandler",
]

import datetime
import re
import time
from typing import Optional
from typing_extensions import Self

import jinja2
import pydantic

from common.application.base import ICommand
from common.domain.value_objects import ID
from infrastructure.llm import IInferenceEngine
from data_preparation.application import constants
from data_preparation.application.interfaces import IUnitOfWork
from data_preparation.domain.entities import ChatExport, ParsedMessage, Thread
from data_preparation.domain.value_objects import DateUnixtime


_BATCH_SIZE_DIALOGUE_DISENTANGLEMENT = 20
_DIALOGUE_DISENTANGLEMENT_TEMPLATE_NAME = 'thread_decision.jinja2'



class Command(ICommand):
    chat_export_id: ChatExport.ChatID


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

            return self

    class ParsedThreadDecision(pydantic.BaseModel):
        error_message: Optional[str]
        thread_decision: Optional["CommandHandler.ThreadDecision"]

        @pydantic.model_validator(mode='after')
        def validate_error_and_decision(self) -> Self:
            if self.error_message is not None:
                assert self.thread_decision is None
            else:
                assert self.thread_decision is not None

            return self

    def __init__(
            self,
            uow: IUnitOfWork,
            inference_engine: IInferenceEngine,
    ):
        self._uow = uow
        self._inference_engine = inference_engine
        self._active_threads: dict[ID, Thread] = {}

        self._total_classification_time: float = 0.0
        self._processed_messages_count: int = 0

        template_loader = jinja2.FileSystemLoader(str(constants.PROMPTS_DIR))
        self._jinja_env = jinja2.Environment(loader=template_loader, autoescape=False)

        self._disentanglement_template = self._jinja_env.get_template(_DIALOGUE_DISENTANGLEMENT_TEMPLATE_NAME)

    async def handle(self, command: Command) -> None:
        chat_export: ChatExport = await self._uow.chat_export.get_by_id_or_raise(command.chat_export_id)

        if chat_export.status != ChatExport.Status.INGESTED:
            print(
                f"ChatExport {chat_export.chat_id.value} is in {chat_export.status.value} state, "
                f"skipping thread processing."
            )
            return

        target_seq_numbers: list[int] = await self._uow.parsed_message.get_target_user_sequence_numbers_by_chat_export_id(
            chat_export_id=command.chat_export_id,
            target_user_name=chat_export.target_user_name,
        )
        target_positions: list[int] = [seq - 1 for seq in target_seq_numbers]

        segments: list[tuple[int, int]] = self._build_segments(
            target_positions=target_positions,
            total_messages=chat_export.n_messages,
        )

        if not segments:
            print(
                f"ChatExport {chat_export.chat_id.value} has no messages from target user "
                f"'{chat_export.target_user_name.value}'; marking as FAILED."
            )
            chat_export.mark_failed()
            self._uow.chat_export.update(chat_export)
            await self._uow.commit()
            return

        covered: int = sum(end - start for start, end in segments)
        print(
            f"ChatExport {chat_export.chat_id.value}: built {len(segments)} segment(s) "
            f"covering {covered}/{chat_export.n_messages} messages."
        )

        for segment_idx, (start, end) in enumerate(segments, 1):
            self._active_threads = {}
            await self._restore_active_threads_for_segment(
                chat_export_id=command.chat_export_id,
                seg_start_pos=start,
                seg_end_pos=end,
            )
            seg_len: int = end - start
            print(
                f"Segment {segment_idx}/{len(segments)}: positions [{start}:{end}] "
                f"({seg_len} msgs, restored {len(self._active_threads)} active thread(s))"
            )

            for in_seg_offset in range(0, seg_len, _BATCH_SIZE_DIALOGUE_DISENTANGLEMENT):
                global_offset: int = start + in_seg_offset
                batch_limit: int = min(
                    _BATCH_SIZE_DIALOGUE_DISENTANGLEMENT,
                    seg_len - in_seg_offset,
                )

                batch: list[ParsedMessage] = await self._uow.parsed_message.get_batch_by_chat_export_id(
                    chat_export_id=command.chat_export_id,
                    offset=global_offset,
                    limit=batch_limit,
                )

                sub_offset: int = global_offset + 1
                sub_limit: int = max(
                    0,
                    min(
                        _BATCH_SIZE_DIALOGUE_DISENTANGLEMENT + constants.W_SUB,
                        end - sub_offset,
                    ),
                )
                if sub_limit > 0:
                    messages_sub: list[ParsedMessage] = await self._uow.parsed_message.get_batch_by_chat_export_id(
                        chat_export_id=command.chat_export_id,
                        offset=sub_offset,
                        limit=sub_limit,
                    )
                else:
                    messages_sub = []

                await self._process_batch(
                    messages=batch,
                    messages_sub=messages_sub,
                )
                await self._uow.commit()

        chat_export.mark_ready()
        self._uow.chat_export.update(chat_export)
        await self._uow.commit()

        if self._processed_messages_count > 0:
            avg_time = self._total_classification_time / self._processed_messages_count
            print(f"Processed messages: {self._processed_messages_count}")
            print(f"avg classification time: {avg_time:.4f} seconds")

    async def _process_batch(
            self,
            messages: list[ParsedMessage],
            messages_sub: list[ParsedMessage],
    ) -> None:
        for i, message in enumerate(messages, 1):
            await self._process_single_message(
                i=i,
                message=message,
                messages_sub=messages_sub,
            )

    def _build_segments(
            self,
            target_positions: list[int],
            total_messages: int,
    ) -> list[tuple[int, int]]:
        if not target_positions:
            return []

        raw_segments: list[tuple[int, int]] = []
        cursor: int = 0
        while cursor < len(target_positions):
            first: int = target_positions[cursor]
            start: int = max(0, first - constants.N_PREAMBLE)

            last: int = first
            nxt: int = cursor + 1
            while nxt < len(target_positions):
                gap: int = target_positions[nxt] - last - 1
                if gap >= constants.N_SILENCE_THRESHOLD:
                    break
                last = target_positions[nxt]
                nxt += 1

            end: int = min(total_messages, last + 1 + constants.W_SUB)
            raw_segments.append((start, end))
            cursor = nxt

        merged: list[tuple[int, int]] = []
        for seg_start, seg_end in raw_segments:
            if merged and seg_start <= merged[-1][1]:
                prev_start, prev_end = merged[-1]
                merged[-1] = (prev_start, max(prev_end, seg_end))
            else:
                merged.append((seg_start, seg_end))

        return merged

    async def _restore_active_threads_for_segment(
            self,
            chat_export_id: ChatExport.ChatID,
            seg_start_pos: int,
            seg_end_pos: int,
    ) -> None:
        seq_start: int = seg_start_pos + 1
        seq_end: int = seg_end_pos

        thread_ids: list[ID] = await self._uow.parsed_message.get_recent_thread_ids_in_range(
            chat_export_id=chat_export_id,
            seq_start=seq_start,
            seq_end=seq_end,
            limit=constants.N_ACTIVE_THREADS,
        )
        if not thread_ids:
            return

        for thread_id in thread_ids:
            thread: Optional[Thread] = await self._uow.thread.get_by_id_optional(thread_id)
            if thread is None:
                continue
            self._active_threads[thread.id] = thread

    async def _process_single_message(
            self,
            i: int,
            message: ParsedMessage,
            messages_sub: list[ParsedMessage],
    ) -> None:
        if message.thread_id is not None:
            return

        start_time = time.perf_counter()
        determined_thread: Optional[Thread] = await self._determine_message_thread(
            i=i,
            message=message,
            messages_sub=messages_sub,
        )

        if determined_thread is not None:
            determined_thread.add_message(message)
            message.assign_to_thread(determined_thread.id)
            self._uow.thread.update(determined_thread)
            self._uow.parsed_message.update(message)

        self._remove_outdated_threads(message.sequence_number)

        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        self._total_classification_time += elapsed_time
        self._processed_messages_count += 1

        print(f"Message Sequence {message.sequence_number.value} | Classification time: {elapsed_time:.4f} seconds")

    async def _determine_message_thread(
            self,
            i: int,
            message: ParsedMessage,
            messages_sub: list[ParsedMessage],
    ) -> Optional[Thread]:
        if message.has_reply_message_id():
            thread: Optional[Thread] = await self._determine_replied_message_thread(message)
            if thread is not None:
                print(f"Message {message.external_id.value} assigned to thread {thread.id.value} based on reply_to_message_id {message.reply_to_message_id}")
                return thread

        return await self._determine_non_replied_message_thread(
            i=i,
            message=message,
            messages_sub=messages_sub,
        )

    async def _determine_replied_message_thread(
            self,
            message: ParsedMessage,
    ) -> Optional[Thread]:
        thread: Optional[Thread] = self._get_thread_from_active_threads_by_message_id(message.reply_to_message_id)
        if thread is not None:
            return thread

        reply_message: Optional[ParsedMessage] = await self._uow.parsed_message.get_by_id_optional(
            message.reply_to_message_id,
        )
        if reply_message is None or reply_message.thread_id is None:
            return None

        thread = await self._uow.thread.get_by_id_optional(reply_message.thread_id)
        if thread is None:
            return None

        self._add_thread_to_active(thread)
        return thread

    async def _determine_non_replied_message_thread(
            self,
            i: int,
            message: ParsedMessage,
            messages_sub: list[ParsedMessage],
    ) -> Thread:
        fast_track_thread: Optional[Thread] = await self._try_fast_track_quick_reply(message)
        if fast_track_thread is not None:
            return fast_track_thread

        clipped_messages_sub: list[ParsedMessage] = self._clip_messages_sub(
            messages_sub=messages_sub,
            i=i,
        )
        thread_mapping: dict[int, ID] = self._generate_thread_mapping()

        decision: "CommandHandler.ThreadDecision" = await self._get_thread_decision_with_retries(
            message=message,
            clipped_messages_sub=clipped_messages_sub,
            thread_mapping=thread_mapping,
        )

        return await self._apply_thread_decision(
            decision=decision,
            message=message,
        )

    async def _try_fast_track_quick_reply(
            self,
            message: ParsedMessage,
    ) -> Optional[Thread]:
        if not self._active_threads:
            new_thread: Thread = await self._create_thread_and_add_to_active(message)
            return new_thread

        words = re.findall(r'\w+', message.text.value)

        if len(words) > constants.MAX_WORDS_QUICK_REPLY:
            return None

        most_recent_thread = max(
            self._active_threads.values(),
            key=lambda t: t.recent_messages[-1].date_unixtime.value
        )

        last_message_time = most_recent_thread.recent_messages[-1].date_unixtime.value
        current_message_time = message.date_unixtime.value

        time_delta = current_message_time - last_message_time
        if time_delta <= constants.MAX_SECONDS_QUICK_REPLY:
            print(f"Fast-track quick reply:'{message.text.value}' to thread {most_recent_thread.id.value}")
            return most_recent_thread

        return None

    async def _get_thread_decision_with_retries(
            self,
            message: ParsedMessage,
            clipped_messages_sub: list[ParsedMessage],
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
                print(f"Attempt to parse thread decision failed: {parsed_thread_decision.error_message}. Retrying...")
                warning_message += f"{parsed_thread_decision.error_message}\n"
                continue

            print(f"Successfully parsed thread decision: {parsed_thread_decision.thread_decision}")
            return parsed_thread_decision.thread_decision

        return self.ThreadDecision(
            thread_id=None,
            is_new_thread=True,
        )

    async def _apply_thread_decision(
            self,
            decision: "CommandHandler.ThreadDecision",
            message: ParsedMessage,
    ) -> Thread:
        if decision.is_new_thread:
            new_thread: Thread = await self._create_thread_and_add_to_active(message)
            return new_thread

        return self._get_thread_from_active_threads_by_id(
            thread_id=decision.thread_id,
        )

    def _add_thread_to_active(
            self,
            thread: Thread,
    ) -> None:
        self._active_threads[thread.id] = thread

    def _clip_messages_sub(
            self,
            messages_sub: list[ParsedMessage],
            i: int,
    ) -> list[ParsedMessage]:
        start_idx = i - 1
        end_idx = start_idx + constants.W_SUB
        return messages_sub[start_idx:end_idx]

    def _generate_thread_mapping(self) -> dict[int, ID]:
        return {
            idx: thread_id for idx, thread_id in enumerate(self._active_threads.keys(), 1)
        }

    def _get_prompt(
            self,
            message: ParsedMessage,
            clipped_messages_sub: list[ParsedMessage],
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
            system_prompt=constants.DIALOGUE_DISENTANGLEMENT_SYSTEM_PROMPT,
            user_prompt=prompt,
            lora_path=None,
            max_tokens=constants.MAX_TOKENS_THREAD_DECISION,
            temp=constants.TEMP_THREAD_DECISION,
            assistant_prefill="number:",
            priority=10,
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
        match = re.search(r'\d+', raw_thread_decision)

        if not match:
            return None

        try:
            return int(match.group())
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
            "last_timestamp": last_timestamp,
            "messages": self._format_thread_messages(messages=recent_messages),
        }

    def _format_thread_messages(
            self,
            messages: list[ParsedMessage],
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
            message: ParsedMessage,
    ) -> dict:
        return {
            "time_display": self._format_timestamp(message.date_unixtime),
            "sender": message.from_user.value,
            "text": message.text.value,
        }

    def _format_future_messages(
            self,
            messages_sub: list[ParsedMessage],
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

    async def _create_thread_and_add_to_active(
            self,
            message: ParsedMessage,
    ) -> Thread:
        new_thread = Thread.create(message=message)
        self._uow.thread.create(new_thread)
        await self._uow.flush()
        self._add_thread_to_active(new_thread)

        return new_thread

    def _get_thread_from_active_threads_by_id(
            self,
            thread_id: ID,
    ) -> Optional[Thread]:
        thread = self._active_threads.get(thread_id)
        if thread is not None:
            return thread

        raise ValueError(f"Thread with id {thread_id} not found in active threads")

    def _get_thread_from_active_threads_by_message_id(
            self,
            message_id: ID,
    ) -> Optional[Thread]:
        for thread in self._active_threads.values():
            for message in thread.recent_messages:
                if message.id == message_id:
                    return thread

            for message in thread.uncommitted_messages:
                if message.id == message_id:
                    return thread

        return None

    def _remove_outdated_threads(
            self,
            current_seq_num: ParsedMessage.SequenceNumber,
    ) -> None:
        self._remove_stale_threads(current_seq_num)
        self._enforce_active_threads_limit()

    def _remove_stale_threads(
            self,
            current_seq_num: ParsedMessage.SequenceNumber,
    ) -> None:
        for thread in list(self._active_threads.values()):
            last_message_seq_num: ParsedMessage.SequenceNumber = thread.recent_messages[-1].sequence_number
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
