__all__ = [
    "DateUnixtime",
    "ExportFileKey",
    "DatasetFileKey",
]

from common.domain.value_objects import ValueObject


class DateUnixtime(ValueObject):
    value: int

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, DateUnixtime)

        return self.value == other.value


class ExportFileKey(ValueObject):
    value: str

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, ExportFileKey)

        return self.value == other.value

    def __str__(self) -> str:
        return self.value


class DatasetFileKey(ValueObject):
    value: str

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, DatasetFileKey)

        return self.value == other.value

    def __str__(self) -> str:
        return self.value
