import pytest
from bot_operations.application.features import assign_neuroclone_to_bot, create_bot
from bot_operations.domain.entities import Bot
from bot_operations.infrastructure.in_memory import InMemoryUnitOfWork
from common.domain.value_objects import ID, OwnerTelegramID, ReplyPeriod


async def _register_pending_bot(uow: InMemoryUnitOfWork, owner_id: int=42, token: str='t:abc', name: str='Bot') -> Bot:
    create_handler = create_bot.CommandHandler(uow=uow)
    await create_handler.handle(create_bot.Command(owner_id=OwnerTelegramID(value=owner_id), bot_name=Bot.Name(value=name), bot_token=Bot.Token(value=token)))
    bot = await uow.bot.get_by_token_optional(Bot.Token(value=token))
    assert bot is not None
    return bot


@pytest.mark.asyncio
async def test_assignment_persists_neuroclone_link() -> None:
    uow = InMemoryUnitOfWork()
    bot = await _register_pending_bot(uow)
    assign_handler = assign_neuroclone_to_bot.CommandHandler(uow=uow)
    neuroclone_id = ID.create()
    await assign_handler.handle(assign_neuroclone_to_bot.Command(owner_id=OwnerTelegramID(value=42), neuroclone_id=neuroclone_id, reply_period=ReplyPeriod(value=5)))
    refreshed = await uow.bot.get_by_id_or_raise(bot.id)
    assert refreshed.neuroclone_id == neuroclone_id
    assert refreshed.reply_period == ReplyPeriod(value=5)


@pytest.mark.asyncio
async def test_no_pending_bot_results_in_noop() -> None:
    uow = InMemoryUnitOfWork()
    assign_handler = assign_neuroclone_to_bot.CommandHandler(uow=uow)
    result = await assign_handler.handle(assign_neuroclone_to_bot.Command(owner_id=OwnerTelegramID(value=42), neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=5)))
    assert result is None
    new_events = [e for e in uow.outbox if isinstance(e, Bot.NeuroCloneAssigned)]
    assert new_events == []


@pytest.mark.asyncio
async def test_assignment_picks_only_bots_without_neuroclone() -> None:
    uow = InMemoryUnitOfWork()
    bot_with_clone = await _register_pending_bot(uow, token='a:abc', name='Already')
    bot_with_clone.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=10))
    uow.bot.update(bot_with_clone)
    fresh_bot = await _register_pending_bot(uow, token='b:abc', name='Fresh')
    new_clone = ID.create()
    assign_handler = assign_neuroclone_to_bot.CommandHandler(uow=uow)
    await assign_handler.handle(assign_neuroclone_to_bot.Command(owner_id=OwnerTelegramID(value=42), neuroclone_id=new_clone, reply_period=ReplyPeriod(value=3)))
    refreshed_fresh = await uow.bot.get_by_id_or_raise(fresh_bot.id)
    assert refreshed_fresh.neuroclone_id == new_clone
    assert refreshed_fresh.reply_period == ReplyPeriod(value=3)


@pytest.mark.asyncio
async def test_assignment_emits_event() -> None:
    uow = InMemoryUnitOfWork()
    await _register_pending_bot(uow)
    assign_handler = assign_neuroclone_to_bot.CommandHandler(uow=uow)
    await assign_handler.handle(assign_neuroclone_to_bot.Command(owner_id=OwnerTelegramID(value=42), neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=5)))
    assigned_events = [e for e in uow.outbox if isinstance(e, Bot.NeuroCloneAssigned)]
    assert len(assigned_events) == 1
