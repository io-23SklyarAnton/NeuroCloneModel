__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import json
from io import BytesIO

import jinja2
import pydantic

from common.application.base import ICommand, Response
from common.domain.value_objects import FileReference, ReplyPeriod, UserName
from data_preparation.application import constants
from data_preparation.application.interfaces import IStorage, IUnitOfWork
from data_preparation.domain.entities import ChatExport, ParsedMessage, TrainingDataset
from utils import get_now_datetime


class Command(ICommand):
    chat_export_id: ChatExport.ChatID


class CommandHandler:
    _BUCKET_NAME = "imitation-datasets"

    class ImitationPair(pydantic.BaseModel):
        context: str
        expected_response: str

    class _BuildResult(pydantic.BaseModel):
        pairs: list["CommandHandler.ImitationPair"]
        n_target_messages: int

    def __init__(
            self,
            uow: IUnitOfWork,
            storage: IStorage,
    ) -> None:
        self._uow = uow
        self._storage = storage

        template_loader = jinja2.FileSystemLoader(searchpath=constants.PROMPTS_DIR)
        jinja_env = jinja2.Environment(
            loader=template_loader,
            autoescape=False,
        )
        self._template = jinja_env.get_template(constants.IMITATION_CONTEXT_TEMPLATE_NAME)

    async def handle(
            self,
            command: Command,
    ) -> Response:
        chat_export: ChatExport = await self._uow.chat_export.get_by_id_or_raise(command.chat_export_id)

        build_result: CommandHandler._BuildResult = await self._build_pairs(
            chat_export_id=chat_export.id,
            target_user=chat_export.target_user_name,
        )
        pairs: list[CommandHandler.ImitationPair] = build_result.pairs

        system_prompt: str = self._build_system_prompt(chat_export.target_user_name)
        file_reference: FileReference = self._make_file_reference(command.chat_export_id)
        content: BytesIO = self._serialize_dataset(
            dataset=pairs,
            system_prompt=system_prompt,
        )

        await self._storage.save(
            file_object=content,
            file_reference=file_reference,
        )

        reply_period: ReplyPeriod = self._compute_reply_period(
            n_total_messages=chat_export.n_messages,
            n_target_messages=build_result.n_target_messages,
        )

        dataset: TrainingDataset = TrainingDataset.create(
            owner_id=chat_export.owner_id,
            target_user=chat_export.target_user_name,
            source_chat_export_id=chat_export.id,
            file_reference=file_reference,
            n_pairs=len(pairs),
            built_at=get_now_datetime(),
            reply_period=reply_period,
        )
        self._uow.training_dataset.create(dataset)
        await self._uow.commit()

        return Response(message=f"Built training dataset with {len(pairs)} pairs.")

    async def _build_pairs(
            self,
            chat_export_id: ChatExport.ChatID,
            target_user: UserName,
    ) -> _BuildResult:
        threads = await self._uow.thread.get_all_by_chat_export_id(chat_export_id)
        pairs: list[CommandHandler.ImitationPair] = []
        n_target_messages: int = 0
        for thread in threads:
            messages = await self._uow.parsed_message.get_by_thread_id(thread.id)
            pairs.extend(self._pairs_from_thread(messages, target_user))
            n_target_messages += sum(
                1 for m in messages if m.from_user.value == target_user.value
            )

        return CommandHandler._BuildResult(
            pairs=pairs,
            n_target_messages=n_target_messages,
        )

    def _pairs_from_thread(
            self,
            messages: list[ParsedMessage],
            target_user: UserName,
    ) -> list[ImitationPair]:
        pairs: list[CommandHandler.ImitationPair] = []
        context: list[ParsedMessage] = []
        for message in messages:
            if self._is_target_response(
                    message=message,
                    target_user=target_user,
                    context=context,
            ):
                pairs.append(self._build_pair(
                    context=context,
                    response=message,
                ))

            context.append(message)

        return pairs

    def _is_target_response(
            self,
            message: ParsedMessage,
            target_user: UserName,
            context: list[ParsedMessage],
    ) -> bool:
        return (
                message.from_user.value == target_user.value
                and message.message_type == ParsedMessage.Type.TEXT
                and bool(context)
        )

    def _build_pair(
            self,
            context: list[ParsedMessage],
            response: ParsedMessage,
    ) -> ImitationPair:
        return CommandHandler.ImitationPair(
            context=self._format_context(context),
            expected_response=response.text.value,
        )

    def _format_context(
            self,
            messages: list[ParsedMessage],
    ) -> str:
        window = messages[-constants.MAX_CONTEXT_MESSAGES_IMITATION:]
        messages_data = [
            {
                "sender": msg.from_user.value,
                "text": msg.text.value,
            }
            for msg in window

        ]
        return self._template.render(messages=messages_data)

    def _serialize_dataset(
            self,
            dataset: list[ImitationPair],
            system_prompt: str,
    ) -> BytesIO:
        lines: list[str] = [
            json.dumps(
                {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": pair.context},
                        {"role": "assistant", "content": pair.expected_response},
                    ]
                },
                ensure_ascii=False,
            )
            for pair in dataset
        ]
        return BytesIO("\n".join(lines).encode("utf-8"))

    @classmethod
    def _make_file_reference(cls, chat_export_id: ChatExport.ChatID) -> FileReference:
        timestamp: str = get_now_datetime().strftime("%Y%m%d_%H%M%S")
        return FileReference(
            bucket=cls._BUCKET_NAME,
            key=f"{chat_export_id.value}_{timestamp}.jsonl",
        )

    @staticmethod
    def _build_system_prompt(target_user: UserName) -> str:
        return constants.IMITATION_SYSTEM_PROMPT.format(target_user=target_user.value)

    @staticmethod
    def _compute_reply_period(
            n_total_messages: int,
            n_target_messages: int,
    ) -> ReplyPeriod:
        if n_target_messages <= 0:
            return ReplyPeriod(value=max(n_total_messages, 1))

        ratio: int = max(1, n_total_messages // n_target_messages)
        return ReplyPeriod(value=ratio)
