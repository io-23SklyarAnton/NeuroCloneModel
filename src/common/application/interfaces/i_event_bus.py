__all__ = ["IEventBus"]

import abc

from common.application.base import ICommand


class IEventBus(abc.ABC):
    @abc.abstractmethod
    async def group_apply(self, commands: list[ICommand]) -> None: ...
