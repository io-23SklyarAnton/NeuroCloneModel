__all__ = ["Thread"]

from domain.entities.base import Aggregate
from domain.value_objects import ID


class Thread(Aggregate):
    def __init__(
            self,
            id_: ID,
    ):
        super().__init__()
        self._id = id_

    @property
    def id(self) -> ID:
        return self._id
