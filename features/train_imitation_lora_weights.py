import json

import pydantic
import jinja2
from pathlib import Path

import constants
from domain.entities.chat import Chat
from domain.entities.message import Message
from features import interfaces
from features.base import ICommand
from llm import IInferenceEngine


class Command(ICommand):
    chat_id: Chat.ExternalID
    target_user: Message.UserName
    data_dir: Path
    adapter_path: Path


class CommandHandler:
    class ImitationPair(pydantic.BaseModel):
        context: str
        expected_response: str

    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
            inference_engine: IInferenceEngine,
    ):
        self._uow = uow
        self._inference_engine = inference_engine

        template_loader = jinja2.FileSystemLoader(searchpath=constants.PROMPTS_DIR)
        self._jinja_env = jinja2.Environment(loader=template_loader, autoescape=False)

        self._imitation_template = self._jinja_env.get_template(
            constants.IMITATION_CONTEXT_TEMPLATE_NAME
        )

    async def handle(self, command: Command) -> list[ImitationPair]:
        threads = await self._uow.thread.get_all_by_chat_id(command.chat_id)
        dataset: list[CommandHandler.ImitationPair] = []

        for thread in threads:
            messages = await self._uow.message.get_by_thread_id(thread.id)
            thread_pairs = self._process_thread_messages(
                messages=messages,
                target_user=command.target_user,
            )
            dataset.extend(thread_pairs)

        await self._run_training_pipeline(
            dataset=dataset,
            target_user=command.target_user,
            data_dir=command.data_dir,
            adapter_path=command.adapter_path,
        )

        return dataset

    def _process_thread_messages(
            self,
            messages: list[Message],
            target_user: Message.UserName,
    ) -> list[ImitationPair]:
        pairs: list[CommandHandler.ImitationPair] = []
        context_messages: list[Message] = []

        for message in messages:
            if message.from_user == target_user and context_messages:
                context_text = self._format_context(context_messages)
                expected_text = message.text.value

                pairs.append(
                    self.ImitationPair(
                        context=context_text,
                        expected_response=expected_text,
                    )
                )

            context_messages.append(message)

        return pairs

    def _format_context(self, messages: list[Message]) -> str:
        messages_data = [
            {
                "sender": msg.from_user.value,
                "text": msg.text.value,
            }
            for msg in messages[-constants.MAX_CONTEXT_MESSAGES_IMITATION:]
        ]

        return self._imitation_template.render(messages=messages_data)

    async def _run_training_pipeline(
            self,
            dataset: list[ImitationPair],
            target_user: Message.UserName,
            data_dir: Path,
            adapter_path: Path,
    ) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        adapter_path.mkdir(parents=True, exist_ok=True)

        train_file_path = data_dir / "train.jsonl"
        system_prompt = self._get_system_prompt(target_user)
        with open(train_file_path, "w", encoding="utf-8") as f:
            for pair in dataset:
                json_line = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": pair.context},
                        {"role": "assistant", "content": pair.expected_response}
                    ]
                }
                f.write(json.dumps(json_line, ensure_ascii=False) + "\n")

        await self._inference_engine.train_lora(
            data_dir=str(data_dir),
            adapter_path=str(adapter_path),
        )

    def _get_system_prompt(self, target_user: Message.UserName) -> str:
        return constants.IMITATION_SYSTEM_PROMPT.format(target_user=target_user.value)
