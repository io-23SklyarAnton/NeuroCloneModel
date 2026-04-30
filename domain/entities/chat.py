__all__ = ["Chat"]

from domain.entities.base import Aggregate
from domain.value_objects import ValueObject


class Chat(Aggregate):
    class ExternalID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, Chat.ExternalID)

            return self.value == other.value

    def __init__(
            self,
            external_id: ExternalID,
            n_messages: int
    ):
        super().__init__()
        self._external_id = external_id
        self._n_messages = n_messages

    @property
    def id(self) -> ExternalID:
        return self._external_id

    @property
    def external_id(self) -> ExternalID:
        return self._external_id

    @property
    def n_messages(self) -> int:
        return self._n_messages
