__all__ = [
    "DateUnixtime",
]

from common.domain.value_objects import ValueObject


class DateUnixtime(ValueObject):
    value: int

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, DateUnixtime)

        return self.value == other.value
