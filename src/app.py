import asyncio
import logging

from aiogram import Bot, Dispatcher
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka

import config
from bot_operations.infrastructure.aiogram_bot_runner import AiogramBotRunnerService
from bot_operations.infrastructure.bot_reconciler import BotReconciler
from common.infrastructure.db.utils import init_db
from dependencies import AppProvider
from handlers import create_bot_router, start_router


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _resolve_main_bot_token() -> str:
    token = config.MAIN_BOT_TOKEN
    if not token:
        raise RuntimeError("MAIN_BOT_TOKEN env var is required to run the main bot.")
    return token


async def main() -> None:
    _setup_logging()
    init_db()

    main_bot_token: str = _resolve_main_bot_token()

    dp: Dispatcher = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(create_bot_router)

    bot_runner: AiogramBotRunnerService = AiogramBotRunnerService()

    container = make_async_container(AppProvider(bot_runner=bot_runner))
    bot_runner.attach_container(container)
    setup_dishka(container=container, router=dp)

    reconciler: BotReconciler = BotReconciler(
        runner=bot_runner,
        container=container,
        interval_seconds=10.0,
    )
    await reconciler.start()

    main_bot: Bot = Bot(token=main_bot_token)

    try:
        await dp.start_polling(main_bot)
    finally:
        await reconciler.stop()
        await bot_runner.shutdown()
        await main_bot.session.close()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
