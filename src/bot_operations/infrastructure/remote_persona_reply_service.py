__all__ = ["RemotePersonaReplyService"]

import asyncio
import logging
import uuid
from typing import Optional

from bot_operations.application.interfaces import (
    ChatContextMessage,
    PersonaReplyService,
)


_logger = logging.getLogger("bot_operations.remote_persona_reply_service")


class RemotePersonaReplyService(PersonaReplyService):
    def __init__(
            self,
            timeout_seconds: float,
    ) -> None:
        self._timeout_seconds = timeout_seconds

    async def generate_reply(
            self,
            neuroclone_id: uuid.UUID,
            context: list[ChatContextMessage],
    ) -> Optional[str]:
        from infrastructure.celery.celery_app import celery_app
        from infrastructure.celery.scheduled_tasks.command_handlers import (
            GeneratePersonaReplyPayload,
            generate_persona_reply_task,
        )

        payload: GeneratePersonaReplyPayload = GeneratePersonaReplyPayload(
            neuroclone_id=neuroclone_id,
            context=context,
        )

        try:
            task_id: str = await asyncio.to_thread(
                lambda: generate_persona_reply_task.apply_async(
                    kwargs={"payload": payload.model_dump(mode="json")},
                ),
            )
        except Exception as exc:
            _logger.error(
                "remote_persona_reply_publish_failed: %s",
                exc,
                exc_info=True,
            )
            return None

        async_result = celery_app.AsyncResult(task_id)
        try:
            return await asyncio.to_thread(
                async_result.get,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            _logger.error(
                "remote_persona_reply_get_failed task_id=%s error=%s",
                task_id, exc,
                exc_info=True,
            )
            return None
        finally:
            await asyncio.to_thread(async_result.forget)
