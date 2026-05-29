__all__ = ["BotReconciler"]

import asyncio
from typing import Optional

from dishka import AsyncContainer

from bot_operations.application.interfaces import IUnitOfWork
from bot_operations.domain.entities import Bot
from bot_operations.infrastructure.aiogram_bot_runner import AiogramBotRunnerService
from common.domain.value_objects import ID


class BotReconciler:
    def __init__(
            self,
            runner: AiogramBotRunnerService,
            container: AsyncContainer,
            interval_seconds: float,
    ) -> None:
        self._runner = runner
        self._container = container
        self._interval_seconds = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None:
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._loop(),
            name="bot_reconciler",
        )

    async def stop(self) -> None:
        if self._task is None:
            return

        self._stop_event.set()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._reconcile_once()
            except Exception as exc:
                print(f"Error during bot reconciliation: {exc}")

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

    async def _reconcile_once(self) -> None:
        desired: dict[ID, Bot] = await self._load_desired_state()
        actual: frozenset[ID] = self._runner.running_bot_ids

        for bot_id, bot in desired.items():
            if bot_id in actual:
                continue
            await self._runner.start(
                bot_id=bot.id,
                token=bot.token,
            )

        for bot_id in actual:
            if bot_id in desired:
                continue
            await self._runner.stop(bot_id)

    async def _load_desired_state(self) -> dict[ID, Bot]:
        async with self._container() as request_container:
            uow: IUnitOfWork = await request_container.get(IUnitOfWork)
            running_bots: list[Bot] = await uow.bot.get_all_running()
            return {bot.id: bot for bot in running_bots}
