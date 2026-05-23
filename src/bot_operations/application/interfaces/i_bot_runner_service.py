__all__ = ["IBotRunnerService"]

import abc

from bot_operations.domain.entities import Bot
from common.domain.value_objects import ID


class IBotRunnerService(abc.ABC):
    @abc.abstractmethod
    async def start(self, bot_id: ID, token: Bot.Token) -> None: ...

    @abc.abstractmethod
    async def stop(self, bot_id: ID) -> None: ...

    @abc.abstractmethod
    async def is_running(self, bot_id: ID) -> bool: ...
