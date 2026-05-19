__all__ = ["router"]

from typing import Optional

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, User as AgUser
from dishka import FromDishka

from domain.entities.user import User
from exceptions.client.malformed_request import MissingUserException
from features import RegisterUserCommand, RegisterUserCommandHandler

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(
        message: Message,
        command_handler: FromDishka[RegisterUserCommandHandler]
) -> None:
    if message.from_user is None:
        raise MissingUserException()

    tg_user: AgUser = message.from_user
    username: Optional[User.Username] = (
        User.Username(value=tg_user.username)
        if tg_user.username is not None
        else None
    )

    command = RegisterUserCommand(
        telegram_id=User.TelegramID(value=tg_user.id),
        username=username,
    )

    result = await command_handler.handle(command)

    await message.answer(result.message)
