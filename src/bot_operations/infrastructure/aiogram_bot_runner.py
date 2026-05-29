__all__ = ["AiogramBotRunnerService"]

import asyncio
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot as AiogramBot, Dispatcher
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka

from bot_operations.application.interfaces import IBotRunnerService
from bot_operations.domain.entities import Bot
from common.domain.value_objects import ID
from handlers import create_live_message_router


_STOP_POLLING_TIMEOUT_SECONDS: float = 5.0


@dataclass
class _RunningBot:
    aiogram_bot: AiogramBot
    dispatcher: Dispatcher
    polling_task: asyncio.Task


class AiogramBotRunnerService(IBotRunnerService):
    def __init__(self) -> None:
        self._container: Optional[AsyncContainer] = None
        self._running: dict[ID, _RunningBot] = {}

    def attach_container(
            self,
            container: AsyncContainer,
    ) -> None:
        self._container = container

    async def start(
            self,
            bot_id: ID,
            token: Bot.Token,
    ) -> None:
        if self._container is None:
            raise RuntimeError(
                "AiogramBotRunnerService has no container attached.",
            )
        if bot_id in self._running:
            return

        aiogram_bot: AiogramBot = AiogramBot(token=token.value)
        dispatcher: Dispatcher = Dispatcher()

        try:
            dispatcher.include_router(create_live_message_router())
            setup_dishka(container=self._container, router=dispatcher)
        except Exception:
            await aiogram_bot.session.close()
            raise

        polling_task: asyncio.Task = asyncio.create_task(
            dispatcher.start_polling(
                aiogram_bot,
                domain_bot_id=bot_id,
            ),
            name=f"secondary_bot_polling:{bot_id.value}",
        )
        polling_task.add_done_callback(
            lambda task: self._on_polling_finished(bot_id=bot_id, task=task),
        )

        self._running[bot_id] = _RunningBot(
            aiogram_bot=aiogram_bot,
            dispatcher=dispatcher,
            polling_task=polling_task,
        )

    async def stop(
            self,
            bot_id: ID,
    ) -> None:
        running: Optional[_RunningBot] = self._running.pop(bot_id, None)
        if running is None:
            return

        try:
            await asyncio.wait_for(
                running.dispatcher.stop_polling(),
                timeout=_STOP_POLLING_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, Exception):
            pass

        if not running.polling_task.done():
            running.polling_task.cancel()

        try:
            await running.polling_task
        except (asyncio.CancelledError, Exception):
            pass

        try:
            await running.aiogram_bot.session.close()
        except Exception:
            pass

    async def is_running(
            self,
            bot_id: ID,
    ) -> bool:
        running: Optional[_RunningBot] = self._running.get(bot_id)
        if running is None:
            return False

        return not running.polling_task.done()

    async def shutdown(self) -> None:
        bot_ids: list[ID] = list(self._running.keys())
        for bot_id in bot_ids:
            await self.stop(bot_id)

    @property
    def running_bot_ids(self) -> frozenset[ID]:
        return frozenset(self._running.keys())

    def _on_polling_finished(
            self,
            bot_id: ID,
            task: asyncio.Task,
    ) -> None:
        if not task.cancelled() and task.exception() is not None:
            print(f"Polling for bot {bot_id.value} finished with exception: {task.exception()}")

        self._running.pop(bot_id, None)
