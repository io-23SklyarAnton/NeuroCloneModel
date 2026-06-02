import pytest
from bot_operations.application.features import create_bot, get_user_bots
from bot_operations.domain.entities import Bot
from bot_operations.infrastructure.in_memory import InMemoryUnitOfWork
from common.domain.value_objects import ID, OwnerTelegramID, ReplyPeriod


async def _create_bot(uow: InMemoryUnitOfWork, owner_id: int, token: str, name: str) -> Bot:
    handler = create_bot.CommandHandler(uow=uow)
    await handler.handle(create_bot.Command(owner_id=OwnerTelegramID(value=owner_id), bot_name=Bot.Name(value=name), bot_token=Bot.Token(value=token)))
    bot = await uow.bot.get_by_token_optional(Bot.Token(value=token))
    assert bot is not None
    return bot


@pytest.mark.asyncio
async def test_returns_empty_for_unknown_owner() -> None:
    uow = InMemoryUnitOfWork()
    handler = get_user_bots.CommandHandler(uow=uow)
    response = await handler.handle(get_user_bots.Command(owner_id=OwnerTelegramID(value=42)))
    assert response.bots == []


@pytest.mark.asyncio
async def test_returns_views_for_owner_bots_only() -> None:
    uow = InMemoryUnitOfWork()
    await _create_bot(uow, owner_id=42, token='a:abc', name='A')
    await _create_bot(uow, owner_id=42, token='b:abc', name='B')
    await _create_bot(uow, owner_id=99, token='c:abc', name='C')
    handler = get_user_bots.CommandHandler(uow=uow)
    response = await handler.handle(get_user_bots.Command(owner_id=OwnerTelegramID(value=42)))
    names = sorted((v.name for v in response.bots))
    assert names == ['A', 'B']


@pytest.mark.asyncio
async def test_view_reflects_current_status() -> None:
    uow = InMemoryUnitOfWork()
    bot = await _create_bot(uow, owner_id=42, token='a:abc', name='A')
    bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=5))
    bot.start_bot()
    uow.bot.update(bot)
    handler = get_user_bots.CommandHandler(uow=uow)
    response = await handler.handle(get_user_bots.Command(owner_id=OwnerTelegramID(value=42)))
    assert len(response.bots) == 1
    assert response.bots[0].status == Bot.BotStatus.RUNNING
