import pytest
from bot_operations.application import constants
from bot_operations.application.features import create_bot
from bot_operations.domain.entities import Bot
from bot_operations.infrastructure.in_memory import InMemoryUnitOfWork
from common.domain.value_objects import OwnerTelegramID


def _make_handler() -> tuple[create_bot.CommandHandler, InMemoryUnitOfWork]:
    uow = InMemoryUnitOfWork()
    handler = create_bot.CommandHandler(uow=uow)
    return (handler, uow)


def _cmd(owner_id: int=42, token: str='111:abc', name: str='Bot') -> create_bot.Command:
    return create_bot.Command(owner_id=OwnerTelegramID(value=owner_id), bot_name=Bot.Name(value=name), bot_token=Bot.Token(value=token))


@pytest.mark.asyncio
async def test_create_bot_persists_aggregate_in_pending_state() -> None:
    handler, uow = _make_handler()
    response = await handler.handle(_cmd())
    assert 'registered' in response.message
    stored = await uow.bot.get_by_owner_id(OwnerTelegramID(value=42))
    assert len(stored) == 1
    assert stored[0].status == Bot.BotStatus.PENDING
    assert stored[0].name == Bot.Name(value='Bot')


@pytest.mark.asyncio
async def test_duplicate_token_short_circuits() -> None:
    handler, uow = _make_handler()
    await handler.handle(_cmd(token='dup:abc'))
    response = await handler.handle(_cmd(token='dup:abc', owner_id=99))
    assert 'already exists' in response.message
    assert await uow.bot.get_by_owner_id(OwnerTelegramID(value=99)) == []


@pytest.mark.asyncio
async def test_owner_bot_limit_enforced() -> None:
    handler, uow = _make_handler()
    for i in range(constants.USER_BOT_LIMIT):
        await handler.handle(_cmd(token=f't{i}:abc', name=f'Bot{i}'))
    response = await handler.handle(_cmd(token='overflow:abc', name='Overflow'))
    assert 'maximum number of bots' in response.message
    bots = await uow.bot.get_by_owner_id(OwnerTelegramID(value=42))
    assert len(bots) == constants.USER_BOT_LIMIT


@pytest.mark.asyncio
async def test_different_owners_have_independent_limits() -> None:
    handler, uow = _make_handler()
    for i in range(constants.USER_BOT_LIMIT):
        await handler.handle(_cmd(owner_id=42, token=f'a{i}:abc', name=f'A{i}'))
    response = await handler.handle(_cmd(owner_id=99, token='b0:abc', name='B0'))
    assert 'registered' in response.message
    assert len(await uow.bot.get_by_owner_id(OwnerTelegramID(value=99))) == 1


@pytest.mark.asyncio
async def test_event_queued_in_outbox_on_success() -> None:
    handler, uow = _make_handler()
    await handler.handle(_cmd())
    created_events = [e for e in uow.outbox if isinstance(e, Bot.EventBotCreated)]
    assert len(created_events) == 1
    assert created_events[0].payload.bot_name == 'Bot'
