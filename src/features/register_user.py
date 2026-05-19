__all__ = [
    "Command",
    "CommandHandler",
    "Response",
]

from typing import Optional

from domain.entities.user import User
from features import interfaces
from features.base import ICommand, Response
from utils import get_now_datetime


class Command(ICommand):
    telegram_id: User.TelegramID
    username: Optional[User.Username]


class CommandHandler:
    def __init__(self, uow: interfaces.IUnitOfWork) -> None:
        self._uow = uow

    async def handle(
            self,
            command: Command,
    ) -> Response:
        user: Optional[User] = await self._uow.user.get_by_id_optional(
            command.telegram_id,
        )

        if user is not None:
            user.update_profile(
                username=command.username,
            )
            self._uow.user.update(user)
            self._uow.commit()

            return Response(message=f"Welcome back!")

        new_user = User.create(
            telegram_id=command.telegram_id,
            username=command.username,
            registered_at=get_now_datetime(),
        )
        self._uow.user.create(new_user)
        self._uow.commit()

        return Response(message=f"Hello! You are registered now.")
