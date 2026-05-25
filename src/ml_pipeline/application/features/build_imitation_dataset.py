__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import json
from io import BytesIO

import pydantic

from common.application.base import ICommand, Response
from ml_pipeline.application import constants
from ml_pipeline.application.interfaces import IStorage, IUnitOfWork
from ml_pipeline.application.services import ImitationContextFormatter
from ml_pipeline.domain.entities import ChatExport, ParsedMessage, TrainingDataset
from ml_pipeline.domain.value_objects import DatasetFileKey
from utils import get_now_datetime


class Command(ICommand):
    chat_export_id: ChatExport.ChatID
    owner_id: TrainingDataset.OwnerTelegramID
    target_user: TrainingDataset.TargetUserName


class CommandHandler:
    _BUCKET_NAME = "imitation-datasets"

    class ImitationPair(pydantic.BaseModel):
        context: str
        expected_response: str

    def __init__(
            self,
            uow: IUnitOfWork,
            storage: IStorage,
            context_formatter: ImitationContextFormatter,
    ) -> None:
        self._uow = uow
        self._storage = storage
        self._context_formatter = context_formatter

    async def handle(
            self,
            command: Command,
    ) -> Response:
        pairs: list[CommandHandler.ImitationPair] = await self._build_pairs(
            chat_export_id=command.chat_export_id,
            target_user=command.target_user,
        )

        system_prompt: str = self._build_system_prompt(command.target_user)
        file_key: DatasetFileKey = self._make_file_key(command.chat_export_id)
        content: BytesIO = self._serialize_dataset(
            dataset=pairs,
            system_prompt=system_prompt,
        )

        await self._storage.save(
            file_object=content,
            file_name=str(file_key),
        )

        dataset: TrainingDataset = TrainingDataset.create(
            owner_id=command.owner_id,
            target_user=command.target_user,
            source_chat_export_ids=[command.chat_export_id],
            file_key=file_key,
            n_pairs=len(pairs),
            built_at=get_now_datetime(),
        )
        self._uow.training_dataset.create(dataset)
        await self._uow.commit()

        return Response(message=f"Built training dataset with {len(pairs)} pairs.")

    async def _build_pairs(
            self,
            chat_export_id: ChatExport.ChatID,
            target_user: TrainingDataset.TargetUserName,
    ) -> list[ImitationPair]:
        threads = await self._uow.thread.get_all_by_chat_export_id(chat_export_id)
        pairs: list[CommandHandler.ImitationPair] = []
        for thread in threads:
            messages = await self._uow.parsed_message.get_by_thread_id(thread.id)
            pairs.extend(self._pairs_from_thread(messages, target_user))

        return pairs

    def _pairs_from_thread(
            self,
            messages: list[ParsedMessage],
            target_user: TrainingDataset.TargetUserName,
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
            target_user: TrainingDataset.TargetUserName,
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
        formatter_messages: list[ImitationContextFormatter.Message] = [
            ImitationContextFormatter.Message(
                sender=message.from_user.value,
                text=message.text.value,
            )
            for message in messages
        ]
        return self._context_formatter.format(formatter_messages)

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

    @staticmethod
    def _make_file_key(
            chat_export_id: ChatExport.ChatID,
    ) -> DatasetFileKey:
        timestamp: str = get_now_datetime().strftime("%Y%m%d_%H%M%S")
        return DatasetFileKey(value=f"{chat_export_id.value}_{timestamp}.jsonl")

    @staticmethod
    def _build_system_prompt(
            target_user: TrainingDataset.TargetUserName,
    ) -> str:
        return constants.IMITATION_SYSTEM_PROMPT.format(target_user=target_user.value)
