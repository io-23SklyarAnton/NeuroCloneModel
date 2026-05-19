import asyncio

from aiogram import Dispatcher, Bot
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka

from dependencies import AppProvider
from handlers import start_router
import config


async def main() -> None:
    dp = Dispatcher()

    dp.include_router(start_router)
    # dp.include_router(launch_bot_router)

    container = make_async_container(AppProvider())
    setup_dishka(container=container, router=dp)

    main_bot = Bot(token=config.MAIN_BOT_TOKEN)

    try:
        await dp.start_polling(main_bot)
    finally:
        await main_bot.session.close()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
