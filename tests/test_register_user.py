import pytest
from common.application.base import Response
from iam.application.features import register_user
from iam.domain.entities import User
from iam.infrastructure.in_memory import InMemoryUnitOfWork


def _cmd(telegram_id: int=42, username: str | None='anton') -> register_user.Command:
    return register_user.Command(telegram_id=User.TelegramID(value=telegram_id), username=User.Username(value=username) if username is not None else None)


@pytest.mark.asyncio
async def test_first_call_creates_user() -> None:
    uow = InMemoryUnitOfWork()
    handler = register_user.CommandHandler(uow=uow)
    response: Response = await handler.handle(_cmd())
    assert 'registered' in response.message
    stored = await uow.user.get_by_id_optional(User.TelegramID(value=42))
    assert stored is not None
    assert stored.username == User.Username(value='anton')


@pytest.mark.asyncio
async def test_second_call_updates_username_and_returns_welcome_back() -> None:
    uow = InMemoryUnitOfWork()
    handler = register_user.CommandHandler(uow=uow)
    await handler.handle(_cmd(telegram_id=42, username='old_name'))
    response = await handler.handle(_cmd(telegram_id=42, username='new_name'))
    assert 'Welcome back' in response.message
    stored = await uow.user.get_by_id_optional(User.TelegramID(value=42))
    assert stored is not None
    assert stored.username == User.Username(value='new_name')


@pytest.mark.asyncio
async def test_null_username_is_accepted() -> None:
    uow = InMemoryUnitOfWork()
    handler = register_user.CommandHandler(uow=uow)
    response = await handler.handle(_cmd(telegram_id=42, username=None))
    assert 'registered' in response.message
    stored = await uow.user.get_by_id_optional(User.TelegramID(value=42))
    assert stored is not None
    assert stored.username is None


@pytest.mark.asyncio
async def test_different_telegram_ids_are_independent() -> None:
    uow = InMemoryUnitOfWork()
    handler = register_user.CommandHandler(uow=uow)
    await handler.handle(_cmd(telegram_id=1, username='user1'))
    await handler.handle(_cmd(telegram_id=2, username='user2'))
    u1 = await uow.user.get_by_id_optional(User.TelegramID(value=1))
    u2 = await uow.user.get_by_id_optional(User.TelegramID(value=2))
    assert u1.username == User.Username(value='user1')
    assert u2.username == User.Username(value='user2')
