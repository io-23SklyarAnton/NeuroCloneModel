import pytest
from common.domain.value_objects import FileReference, OwnerTelegramID, ReplyPeriod, UserName
from model_engine.application.features import train_lora_adapter
from model_engine.domain.entities import NeuroClone
from model_engine.infrastructure.in_memory import InMemoryUnitOfWork
from tests.fakes import InMemoryStorage, StubInferenceEngine


def _setup() -> tuple[train_lora_adapter.CommandHandler, InMemoryUnitOfWork, StubInferenceEngine, InMemoryStorage, NeuroClone]:
    uow = InMemoryUnitOfWork()
    engine = StubInferenceEngine()
    storage = InMemoryStorage()
    nc = NeuroClone.create(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), dataset_file_reference=FileReference(bucket='imitation-datasets', key='7_20260101.jsonl'), reply_period=ReplyPeriod(value=5))
    uow.neuroclone.create(nc)
    handler = train_lora_adapter.CommandHandler(uow=uow, inference_engine=engine, storage=storage)
    return (handler, uow, engine, storage, nc)


@pytest.mark.asyncio
async def test_successful_training_marks_ready_and_sets_adapter() -> None:
    handler, uow, engine, _, nc = _setup()
    await handler.handle(train_lora_adapter.Command(neuroclone_id=nc.id))
    refreshed = await uow.neuroclone.get_by_id_or_raise(nc.id)
    assert refreshed.status == NeuroClone.Status.READY
    assert refreshed.adapter_file_reference == FileReference(bucket='adapters', key=f'{nc.id.value}.safetensors')
    assert len(engine.train_calls) == 1


@pytest.mark.asyncio
async def test_inference_engine_receives_resolved_paths() -> None:
    handler, _, engine, _, nc = _setup()
    await handler.handle(train_lora_adapter.Command(neuroclone_id=nc.id))
    call = engine.train_calls[0]
    assert '7_20260101.jsonl' in call['train_data_path']
    assert f'{nc.id.value}.safetensors' in call['adapter_path']


@pytest.mark.asyncio
async def test_failure_in_inference_engine_marks_neuroclone_failed() -> None:
    handler, uow, engine, _, nc = _setup()
    engine.fail_training_with(RuntimeError('MLX OOM'))
    response = await handler.handle(train_lora_adapter.Command(neuroclone_id=nc.id))
    refreshed = await uow.neuroclone.get_by_id_or_raise(nc.id)
    assert refreshed.status == NeuroClone.Status.FAILED
    assert refreshed.adapter_file_reference is None
    assert 'failed' in response.message.lower()


@pytest.mark.asyncio
async def test_emits_ready_event_on_success() -> None:
    handler, uow, _, _, nc = _setup()
    await handler.handle(train_lora_adapter.Command(neuroclone_id=nc.id))
    ready_events = [e for e in uow.outbox if isinstance(e, NeuroClone.EventNeuroCloneReady)]
    assert len(ready_events) == 1
    assert ready_events[0].payload.owner_telegram_id == OwnerTelegramID(value=42)
    assert ready_events[0].payload.reply_period == 5


@pytest.mark.asyncio
async def test_emits_failed_event_on_failure() -> None:
    handler, uow, engine, _, nc = _setup()
    engine.fail_training_with(RuntimeError('disk full'))
    await handler.handle(train_lora_adapter.Command(neuroclone_id=nc.id))
    failed_events = [e for e in uow.outbox if isinstance(e, NeuroClone.EventNeuroCloneFailed)]
    assert len(failed_events) == 1
