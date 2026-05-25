__all__ = [
    "ImitationContextFormatter",
]

from pathlib import Path

import jinja2
import pydantic

from ml_pipeline.application import constants


class ImitationContextFormatter:
    class Message(pydantic.BaseModel):
        sender: str
        text: str

    def __init__(
            self,
            prompts_dir: Path = constants.PROMPTS_DIR,
            template_name: str = constants.IMITATION_CONTEXT_TEMPLATE_NAME,
            window_size: int = constants.MAX_CONTEXT_MESSAGES_IMITATION,
    ) -> None:
        self._window_size = window_size

        loader: jinja2.FileSystemLoader = jinja2.FileSystemLoader(searchpath=str(prompts_dir))
        env: jinja2.Environment = jinja2.Environment(
            loader=loader,
            autoescape=False,
        )
        self._template: jinja2.Template = env.get_template(template_name)

    def format(
            self,
            messages: list[Message],
    ) -> str:
        window: list[ImitationContextFormatter.Message] = messages[-self._window_size:]
        return self._template.render(
            messages=[message.model_dump() for message in window],
        )
