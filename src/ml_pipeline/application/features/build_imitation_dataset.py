__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

import json
from io import BytesIO

import jinja2
import pydantic

from ml_pipeline.application import constants
from common.application.base import ICommand, Response
from ml_pipeline.application.interfaces import IStorage, IUnitOfWork
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
    ) -> None:
        self._uow = uow
        self._storage = storage

        template_loader = jinja2.FileSystemLoader(searchpath=constants.PROMPTS_DIR)
        jinja_env = jinja2.Environment(
            loader=template_loader,
            autoescape=False,
        )
        self._template = jinja_env.get_template(constants.IMITATION_CONTEXT_TEMPLATE_NAME)

    async def handle(self, command: Command) -> Response:
        pairs: list[CommandHandler.ImitationPair] = await self._build_pairs(
            chat_export_id=command.chat_export_id,
            target_user=command.target_user,
        )

        system_prompt: str = self._build_system_prompt(command.target_user)
        file_key: DatasetFileKey = self._make_file_key(command.chat_export_id)
        content = self._serialize_dataset(
            dataset=pairs,
            system_prompt=system_prompt,
        )

        await self._storage.save(
            file_object=content,
            file_name=str(file_key),
        )

        dataset = TrainingDataset.create(
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

    def _format_context(self, messages: list[ParsedMessage]) -> str:
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
        lines = [
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
    def _make_file_key(chat_export_id: ChatExport.ChatID) -> DatasetFileKey:
        timestamp = get_now_datetime().strftime("%Y%m%d_%H%M%S")
        return DatasetFileKey(value=f"{chat_export_id.value}_{timestamp}.jsonl")

    def _build_system_prompt(self, target_user: TrainingDataset.TargetUserName) -> str:
        return constants.IMITATION_SYSTEM_PROMPT.format(target_user=target_user.value)
