import json
from datetime import datetime
from io import BytesIO

import jinja2
import pydantic

import constants
from domain.entities.chat import Chat
from domain.entities.message import Message
from features import interfaces
from features.base import ICommand
from features.interfaces import IStorage


class Command(ICommand):
    chat_id: Chat.ExternalID
    target_user: Message.UserName


class CommandHandler:
    _BUCKET_NAME = "imitation-datasets"

    class ImitationPair(pydantic.BaseModel):
        context: str
        expected_response: str

    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
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

    async def handle(self, command: Command) -> None:
        dataset: list[CommandHandler.ImitationPair] = await self._build_dataset(
            command.chat_id,
            command.target_user
        )

        system_prompt: str = self._build_system_prompt(command.target_user)
        file_name: str = self._make_file_name(command.chat_id)
        content = self._serialize_dataset(
            dataset=dataset,
            system_prompt=system_prompt,
        )

        self._storage.save(
            bucket_name=self._BUCKET_NAME,
            file_object=content,
            file_name=file_name,
        )

    async def _build_dataset(
            self,
            chat_id: Chat.ExternalID,
            target_user: Message.UserName,
    ) -> list[ImitationPair]:
        threads = await self._uow.thread.get_all_by_chat_id(chat_id)
        dataset: list[CommandHandler.ImitationPair] = []
        for thread in threads:
            messages = await self._uow.message.get_by_thread_id(thread.id)
            dataset.extend(self._pairs_from_thread(messages, target_user))

        return dataset

    def _pairs_from_thread(
            self,
            messages: list[Message],
            target_user: Message.UserName,
    ) -> list[ImitationPair]:
        pairs: list[CommandHandler.ImitationPair] = []
        context: list[Message] = []
        for message in messages:
            if message.from_user == target_user and context:
                pairs.append(self._build_pair(
                    context=context,
                    response=message
                ))

            context.append(message)

        return pairs

    def _build_pair(
            self,
            context: list[Message],
            response: Message,
    ) -> ImitationPair:
        return CommandHandler.ImitationPair(
            context=self._format_context(context),
            expected_response=response.text.value,
        )

    def _format_context(self, messages: list[Message]) -> str:
        window = messages[-constants.MAX_CONTEXT_MESSAGES_IMITATION:] # TODO: make it depend on the token count, not messages count
        messages_data = [
            {
                "sender": msg.from_user.value,
                "text": msg.text.value
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
    def _make_file_name(chat_id: Chat.ExternalID) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{chat_id.value}_{timestamp}.jsonl"

    def _build_system_prompt(self, target_user: Message.UserName) -> str:
        return constants.IMITATION_SYSTEM_PROMPT.format(target_user=target_user.value)
