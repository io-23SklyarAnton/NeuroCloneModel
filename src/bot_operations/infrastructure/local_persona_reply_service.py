__all__ = ["LocalPersonaReplyService"]

import logging
import uuid
from typing import Optional

from bot_operations.application.interfaces import (
    ChatContextMessage,
    PersonaReplyService,
)
from model_engine.application.services import PersonaInferenceService


_logger = logging.getLogger("bot_operations.local_persona_reply_service")


class LocalPersonaReplyService(PersonaReplyService):
    def __init__(
            self,
            persona_inference_service: PersonaInferenceService,
    ) -> None:
        self._persona_inference_service = persona_inference_service

    async def generate_reply(
            self,
            neuroclone_id: uuid.UUID,
            context: list[ChatContextMessage],
    ) -> Optional[str]:
        try:
            return await self._persona_inference_service.generate_reply(
                neuroclone_id=neuroclone_id,
                context=context,
            )
        except Exception as exc:
            _logger.error(
                "local_persona_reply_failed neuroclone_id=%s error=%s",
                neuroclone_id, exc,
                exc_info=True,
            )
            return None
