__all__ = ["User"]

from datetime import datetime
from typing import Optional

from domain.entities.base import Aggregate
from domain.value_objects import ValueObject


class User(Aggregate):
    class TelegramID(ValueObject):
        value: int

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, User.TelegramID)

            return self.value == other.value

        def __hash__(self) -> int:
            return hash(self.value)

    class Username(ValueObject):
        value: str

        def __eq__(self, other: object) -> bool:
            assert isinstance(other, User.Username)

            return self.value == other.value

    def __init__(
            self,
            telegram_id: TelegramID,
            username: Optional[Username],
            registered_at: datetime,
    ) -> None:
        super().__init__()
        self._telegram_id = telegram_id
        self._username = username
        self._registered_at = registered_at

    @property
    def id(self) -> TelegramID:
        return self.telegram_id

    @property
    def telegram_id(self) -> TelegramID:
        return self._telegram_id

    @property
    def username(self) -> Optional[Username]:
        return self._username

    @property
    def registered_at(self) -> datetime:
        return self._registered_at

    @classmethod
    def create(
            cls,
            telegram_id: TelegramID,
            username: Optional[Username],
            registered_at: datetime,
    ) -> "User":
        return cls(
            telegram_id=telegram_id,
            username=username,
            registered_at=registered_at,
        )

    def update_profile(
            self,
            username: Optional[Username],
    ) -> None:
        self._username = username
