from domain.entities import Bot
from domain.value_objects import ID
from features.interfaces import IBotRunnerService


class DummyBotRunnerService(IBotRunnerService):
    async def start(self, bot_id: ID, token: Bot.Token) -> None:
        print(f"Starting bot with ID {bot_id} and token {token}...")

    async def stop(self, bot_id: ID) -> None:
        print(f"Stopping bot with ID {bot_id}...")

    async def is_running(self, bot_id: ID) -> bool:
        print(f"Checking if bot with ID {bot_id} is running...")
        return True
