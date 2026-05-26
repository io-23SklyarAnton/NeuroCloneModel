__all__ = [
    "ChatContextMessage",
    "PersonaReplyService",
]

import uuid
from typing import Optional, Protocol

import pydantic


class ChatContextMessage(pydantic.BaseModel):
    sender: str
    text: str


class PersonaReplyService(Protocol):
    async def generate_reply(
            self,
            neuroclone_id: uuid.UUID,
            context: list[ChatContextMessage],
    ) -> Optional[str]: ...
