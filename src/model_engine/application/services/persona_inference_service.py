__all__ = [
    "ChatContextMessage",
    "PersonaInferenceService",
]

import uuid
from pathlib import Path
from typing import Optional

import jinja2
import pydantic

from common.domain.value_objects import ID
from infrastructure.llm import IInferenceEngine
from model_engine.application import constants
from model_engine.application.interfaces import IUnitOfWork
from model_engine.domain.entities import NeuroClone


class ChatContextMessage(pydantic.BaseModel):
    sender: str
    text: str


class PersonaInferenceService:
    def __init__(
            self,
            uow: IUnitOfWork,
            inference_engine: IInferenceEngine,
            prompts_dir: Path = constants.PROMPTS_DIR,
            template_name: str = constants.IMITATION_CONTEXT_TEMPLATE_NAME,
            system_prompt_template: str = constants.IMITATION_SYSTEM_PROMPT,
            max_tokens: int = constants.PERSONA_REPLY_MAX_TOKENS,
            temperature: float = constants.PERSONA_REPLY_TEMPERATURE,
            priority: int = constants.PERSONA_REPLY_PRIORITY,
            window_size: int = constants.PERSONA_REPLY_CONTEXT_WINDOW,
    ) -> None:
        self._uow = uow
        self._inference_engine = inference_engine
        self._system_prompt_template = system_prompt_template
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._priority = priority
        self._window_size = window_size

        loader: jinja2.FileSystemLoader = jinja2.FileSystemLoader(searchpath=str(prompts_dir))
        env: jinja2.Environment = jinja2.Environment(
            loader=loader,
            autoescape=False,
        )
        self._template: jinja2.Template = env.get_template(template_name)

    async def generate_reply(
            self,
            neuroclone_id: uuid.UUID,
            context: list[ChatContextMessage],
    ) -> Optional[str]:
        neuroclone: Optional[NeuroClone] = await self._uow.neuroclone.get_by_id_or_raise(
            ID(value=neuroclone_id),
        )
        if not neuroclone.is_ready or neuroclone.adapter_file_reference is None:
            return None

        user_prompt: str = self._build_user_prompt(context)
        system_prompt: str = self._system_prompt_template.format(
            target_user=neuroclone.target_user_name.value,
        )

        return await self._inference_engine.generate_async(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            lora_path=neuroclone.adapter_file_reference.full_path,
            max_tokens=self._max_tokens,
            temp=self._temperature,
            priority=self._priority,
        )

    def _build_user_prompt(
            self,
            context: list[ChatContextMessage],
    ) -> str:
        window: list[ChatContextMessage] = context[-self._window_size:]
        messages_data: list[dict[str, str]] = [
            {"sender": message.sender, "text": message.text}
            for message in window
        ]
        return self._template.render(messages=messages_data)
