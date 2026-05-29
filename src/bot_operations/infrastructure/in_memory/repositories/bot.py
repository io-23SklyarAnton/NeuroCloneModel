__all__ = ["InMemoryBotRepository"]

from typing import Optional

from bot_operations.application.interfaces.repositories import IBotRepository
from bot_operations.domain.entities import Bot
from common.domain.entities import Aggregate
from common.domain.value_objects import ID, OwnerTelegramID
from common.infrastructure.db.in_memory_repository import InMemoryBaseRepository


class InMemoryBotRepository(InMemoryBaseRepository[Bot], IBotRepository):
    def __init__(
            self,
            storage: dict[ID, Bot],
            outbox: Optional[list[Aggregate.IDomainEvent]] = None,
    ):
        super().__init__(storage=storage, outbox=outbox)

    async def get_by_id_or_raise(self, bot_id: ID) -> Bot:
        return self.get_or_raise(bot_id)

    async def get_by_id_optional(self, bot_id: ID) -> Optional[Bot]:
        return self.get_optional(bot_id)

    async def get_by_token_optional(self, token: Bot.Token) -> Optional[Bot]:
        for bot in self._storage.values():
            if bot.token == token:
                return bot

        return None

    async def get_by_owner_id(self, owner_id: OwnerTelegramID) -> list[Bot]:
        return [bot for bot in self._storage.values() if bot.owner_id == owner_id]

    async def get_by_owner_id_without_neuroclone(
            self,
            owner_id: OwnerTelegramID,
    ) -> Optional[Bot]:
        for bot in self._storage.values():
            if bot.owner_id == owner_id and bot.neuroclone_id is None:
                return bot

        return None

    async def get_all_running(self) -> list[Bot]:
        return [
            bot
            for bot in self._storage.values()
            if bot.status == Bot.BotStatus.RUNNING
        ]
