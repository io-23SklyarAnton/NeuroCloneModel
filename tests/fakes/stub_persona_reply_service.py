import uuid
from typing import Optional
from bot_operations.application.interfaces import ChatContextMessage, PersonaReplyService


class StubPersonaReplyService(PersonaReplyService):

    def __init__(self, canned_reply: Optional[str]='default-reply') -> None:
        self._canned_reply = canned_reply
        self.calls: list[tuple[uuid.UUID, list[ChatContextMessage]]] = []

    async def generate_reply(self, neuroclone_id: uuid.UUID, context: list[ChatContextMessage]) -> Optional[str]:
        self.calls.append((neuroclone_id, list(context)))
        return self._canned_reply

    def set_reply(self, reply: Optional[str]) -> None:
        self._canned_reply = reply

    def call_count(self) -> int:
        return len(self.calls)
