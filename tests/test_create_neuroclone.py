import pytest
from common.domain.value_objects import FileReference, OwnerTelegramID, ReplyPeriod, UserName
from model_engine.application.features import create_neuroclone
from model_engine.domain.entities import NeuroClone
from model_engine.infrastructure.in_memory import InMemoryUnitOfWork


def _cmd() -> create_neuroclone.Command:
    return create_neuroclone.Command(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), dataset_file_reference=FileReference(bucket='imitation-datasets', key='7_20260101_000000.jsonl'), reply_period=ReplyPeriod(value=8))


@pytest.mark.asyncio
async def test_creates_aggregate_in_preparing_state() -> None:
    uow = InMemoryUnitOfWork()
    handler = create_neuroclone.CommandHandler(uow=uow)
    await handler.handle(_cmd())
    stored = await uow.neuroclone.get_by_owner_id(OwnerTelegramID(value=42))
    assert len(stored) == 1
    nc = stored[0]
    assert nc.status == NeuroClone.Status.PREPARING
    assert nc.target_user_name == UserName(value='Anton')
    assert nc.reply_period == ReplyPeriod(value=8)
    assert nc.dataset_file_reference.full_path == 'imitation-datasets/7_20260101_000000.jsonl'
    assert nc.adapter_file_reference is None


@pytest.mark.asyncio
async def test_emits_neuroclone_created_event() -> None:
    uow = InMemoryUnitOfWork()
    handler = create_neuroclone.CommandHandler(uow=uow)
    await handler.handle(_cmd())
    created_events = [e for e in uow.outbox if isinstance(e, NeuroClone.EventNeuroCloneCreated)]
    assert len(created_events) == 1


@pytest.mark.asyncio
async def test_two_creates_produce_two_independent_aggregates() -> None:
    uow = InMemoryUnitOfWork()
    handler = create_neuroclone.CommandHandler(uow=uow)
    await handler.handle(_cmd())
    await handler.handle(_cmd())
    stored = await uow.neuroclone.get_by_owner_id(OwnerTelegramID(value=42))
    assert len(stored) == 2
    assert stored[0].id != stored[1].id
