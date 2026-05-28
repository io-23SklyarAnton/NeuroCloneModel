__all__ = [
    "ID",
    "ValueObject",
    "UserName",
    "OwnerTelegramID",
    "FileReference",
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
        if other is None:
            return False

        assert isinstance(other, ID)

        return self.value == other.value

    def __repr__(self) -> str:
        return str(self.value)

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)


class UserName(ValueObject):
    value: str

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, UserName)

        return self.value == other.value


class OwnerTelegramID(ValueObject):
    value: int

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, OwnerTelegramID)

        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class FileReference(ValueObject):
    bucket: str
    key: str

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileReference):
            return False

        return self.bucket == other.bucket and self.key == other.key

    def __hash__(self) -> int:
        return hash((self.bucket, self.key))

    @property
    def full_path(self) -> str:
        return f"{self.bucket}/{self.key}"
