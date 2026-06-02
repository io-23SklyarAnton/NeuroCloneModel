from common.application.base import ICommand
from common.application.interfaces import IEventBus


class InMemoryEventBus(IEventBus):

    def __init__(self) -> None:
        self.applied: list[ICommand] = []

    async def group_apply(self, commands: list[ICommand]) -> None:
        self.applied.extend(commands)

    def commands_of_type(self, cmd_type: type) -> list[ICommand]:
        return [c for c in self.applied if isinstance(c, cmd_type)]
