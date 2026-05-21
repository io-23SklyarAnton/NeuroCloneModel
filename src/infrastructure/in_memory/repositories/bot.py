from typing import Optional

from domain.entities.bot import Bot
from domain.value_objects import ID
from features.interfaces.repositories.i_bot import IBotRepository
from infrastructure.in_memory.repositories.base import InMemoryBaseRepository


class InMemoryBotRepository(InMemoryBaseRepository[Bot], IBotRepository):
    def __init__(
            self,
            storage: dict[ID, Bot],
    ):
        super().__init__(storage)

    async def get_by_id_or_raise(self, bot_id: ID) -> Bot:
        return self.get_or_raise(bot_id)

    async def get_by_id_optional(self, bot_id: ID) -> Optional[Bot]:
        return self.get_optional(bot_id)

    async def get_all_by_owner_id(self, owner_id: ID) -> list[Bot]:
        return [
            bot for bot in self._storage.values()
            if bot.owner_id == owner_id
        ]
