import asyncio

from aiogram import Bot, Dispatcher
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka

import config
from bot_operations.infrastructure.aiogram_bot_runner import AiogramBotRunnerService
from bot_operations.infrastructure.bot_reconciler import BotReconciler
from common.infrastructure.db.utils import init_db
from dependencies import AppProvider
from handlers import create_bot_router, start_router


async def main() -> None:
    init_db()

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

    main_bot: Bot = Bot(token=config.MAIN_BOT_TOKEN)

    try:
        await dp.start_polling(main_bot)
    finally:
        await reconciler.stop()
        await bot_runner.shutdown()
        await main_bot.session.close()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
