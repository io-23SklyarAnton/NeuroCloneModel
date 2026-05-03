__all__ = [
    "ID",
    "ValueObject",
    "DateUnixtime",
]

import abc
import uuid

import pydantic


class ValueObject(pydantic.BaseModel, abc.ABC):
    @abc.abstractmethod
    def __eq__(self, other: object) -> bool: ...


class ID(ValueObject):
    value: uuid.UUID

    @classmethod
    def create(cls) -> "ID":
        return cls(value=uuid.uuid4())

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, ID)

        return self.value == other.value

    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)


class DateUnixtime(ValueObject):
    value: int

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, DateUnixtime)

        return self.value == other.value
