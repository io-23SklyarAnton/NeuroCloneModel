import asyncio

from aiogram import Bot, Dispatcher
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka

import config
from dependencies import AppProvider
from handlers import create_bot_router, start_router


async def main() -> None:
    dp: Dispatcher = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(create_bot_router)

    container = make_async_container(AppProvider())
    setup_dishka(container=container, router=dp)

    main_bot: Bot = Bot(token=config.MAIN_BOT_TOKEN)

    try:
        await dp.start_polling(main_bot)
    finally:
        await main_bot.session.close()
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
