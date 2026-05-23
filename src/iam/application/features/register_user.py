__all__ = [
    "Command",
    "CommandHandler",
]

from typing import Optional

from common.application.base import ICommand, Response
from iam.application.interfaces import IUnitOfWork
from iam.domain.entities import User
from utils import get_now_datetime


class Command(ICommand):
    telegram_id: User.TelegramID
    username: Optional[User.Username]


class CommandHandler:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
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
            await self._uow.commit()

            return Response(message=f"Welcome back!")

        new_user = User.create(
            telegram_id=command.telegram_id,
            username=command.username,
            registered_at=get_now_datetime(),
        )
        self._uow.user.create(new_user)
        await self._uow.commit()

        return Response(message=f"Hello! You are registered now.")
