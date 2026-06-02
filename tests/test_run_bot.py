import pytest
from bot_operations.application.features import run_bot
from bot_operations.domain.entities import Bot
from bot_operations.infrastructure.in_memory import InMemoryUnitOfWork
from common.domain.value_objects import ID, OwnerTelegramID, ReplyPeriod


def _pending_bot_with_clone() -> Bot:
    bot = Bot.create(owner_id=OwnerTelegramID(value=42), token=Bot.Token(value='t:abc'), name=Bot.Name(value='TestBot'))
    bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=5))
    return bot


@pytest.mark.asyncio
async def test_starting_unknown_bot_returns_not_found() -> None:
    uow = InMemoryUnitOfWork()
    handler = run_bot.CommandHandler(uow=uow)
    response = await handler.handle(run_bot.Command(bot_id=ID.create()))
    assert 'not found' in response.message.lower()


@pytest.mark.asyncio
async def test_starting_pending_bot_marks_it_running() -> None:
    uow = InMemoryUnitOfWork()
    bot = _pending_bot_with_clone()
    uow.bot.create(bot)
    handler = run_bot.CommandHandler(uow=uow)
    response = await handler.handle(run_bot.Command(bot_id=bot.id))
    assert 'marked as running' in response.message
    refreshed = await uow.bot.get_by_id_or_raise(bot.id)
    assert refreshed.status == Bot.BotStatus.RUNNING


@pytest.mark.asyncio
async def test_starting_bot_without_neuroclone_is_rejected() -> None:
    uow = InMemoryUnitOfWork()
    bot = Bot.create(owner_id=OwnerTelegramID(value=42), token=Bot.Token(value='t:abc'), name=Bot.Name(value='NoClone'))
    uow.bot.create(bot)
    handler = run_bot.CommandHandler(uow=uow)
    response = await handler.handle(run_bot.Command(bot_id=bot.id))
    assert 'not ready' in response.message.lower()
    refreshed = await uow.bot.get_by_id_or_raise(bot.id)
    assert refreshed.status == Bot.BotStatus.PENDING


@pytest.mark.asyncio
async def test_starting_already_running_bot_returns_message() -> None:
    uow = InMemoryUnitOfWork()
    bot = _pending_bot_with_clone()
    bot.start_bot()
    uow.bot.create(bot)
    handler = run_bot.CommandHandler(uow=uow)
    response = await handler.handle(run_bot.Command(bot_id=bot.id))
    assert 'already running' in response.message.lower()
