__all__ = ["Chat"]

from domain.entities.base import Aggregate
from domain.value_objects import ID


class Chat(Aggregate):
    def __init__(
            self,
            id_: ID,
            n_messages: int
    ):
        super().__init__()
        self._id = id_
        self._n_messages = n_messages

    @property
    def id(self) -> ID:
        return self._id

    @property
    def n_messages(self) -> int:
        return self._n_messages
