import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
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


def _build_main_bot(token: str) -> Bot:
    url: Optional[str] = config.TELEGRAM_LOCAL_API_URL
    if not url:
        logging.getLogger("app").info("Main bot using CLOUD API (api.telegram.org)")
        return Bot(token=token)

    logging.getLogger("app").info("Main bot using LOCAL API at %s (is_local=True)", url)
    local_server: TelegramAPIServer = TelegramAPIServer.from_base(url, is_local=True)
    session: AiohttpSession = AiohttpSession(api=local_server)
    return Bot(token=token, session=session)


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

    main_bot: Bot = _build_main_bot(main_bot_token)

    try:
        await dp.start_polling(main_bot)
    finally:
        await reconciler.stop()
        await bot_runner.shutdown()
        await main_bot.session.close()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
