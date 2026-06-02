import json
import pytest
from common.domain.value_objects import FileReference, ID, OwnerTelegramID, ReplyPeriod, UserName
from data_preparation.application.features import build_imitation_dataset
from data_preparation.domain.entities import ChatExport, ParsedMessage, Thread, TrainingDataset
from data_preparation.domain.value_objects import DateUnixtime
from data_preparation.infrastructure.in_memory import InMemoryUnitOfWork
from tests.fakes import InMemoryStorage


def _bootstrap_chat_export(uow: InMemoryUnitOfWork, target_user: str='Anton', chat_id: int=7, n_messages: int=0) -> ChatExport:
    file_reference = FileReference(bucket='chat-exports', key=f'{chat_id}.json')
    export = ChatExport.create(chat_id=ChatExport.ChatID(value=chat_id), owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value=target_user), file_reference=file_reference)
    export.record_message_count(n_messages)
    export.mark_ingested()
    uow.chat_export.create(export)
    return export


def _thread_with_messages(uow: InMemoryUnitOfWork, chat_id: ChatExport.ChatID, messages_spec: list[tuple[str, str, int]]) -> Thread:
    seed_msg = ParsedMessage.create(external_id=ParsedMessage.ExternalID(value=1), reply_to_message_id=None, sequence_number=ParsedMessage.SequenceNumber(value=1), date_unixtime=DateUnixtime(value=0), from_user=UserName(value='seed'), text=ParsedMessage.Text(value=''), chat_export_id=chat_id, message_type=ParsedMessage.Type.TEXT)
    thread = Thread.create(message=seed_msg)
    uow.thread.create(thread)
    for idx, (from_user, text, date) in enumerate(messages_spec, start=1):
        msg = ParsedMessage(id_=ID.create(), external_id=ParsedMessage.ExternalID(value=100 + idx), reply_to_message_id=None, sequence_number=ParsedMessage.SequenceNumber(value=idx), date_unixtime=DateUnixtime(value=date), from_user=UserName(value=from_user), text=ParsedMessage.Text(value=text), chat_export_id=chat_id, thread_id=thread.id, message_type=ParsedMessage.Type.TEXT)
        uow.parsed_message.create(msg)
    return thread


async def _run_build(uow: InMemoryUnitOfWork, storage: InMemoryStorage, chat_id: ChatExport.ChatID) -> build_imitation_dataset.CommandHandler:
    handler = build_imitation_dataset.CommandHandler(uow=uow, storage=storage)
    await handler.handle(build_imitation_dataset.Command(chat_export_id=chat_id))
    return handler


def _decode_jsonl(storage: InMemoryStorage, dataset) -> list[dict]:
    raw = storage._files[dataset.file_reference]
    return [json.loads(line) for line in raw.decode('utf-8').splitlines()]


@pytest.mark.asyncio
async def test_pair_produced_for_target_reply_with_context() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=10)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Alex', 'hi', 1700000000), ('Alex', 'you there?', 1700000020), ('Anton', 'yes', 1700000040)])
    await _run_build(uow, storage, export.chat_id)
    datasets = uow.training_dataset.get_all()
    assert len(datasets) == 1
    dataset = datasets[0]
    pairs = _decode_jsonl(storage, dataset)
    assert len(pairs) == 1
    pair = pairs[0]
    assert 'Act as Anton' in pair['messages'][0]['content']
    assert 'Alex: hi' in pair['messages'][1]['content']
    assert 'Alex: you there?' in pair['messages'][1]['content']
    assert pair['messages'][2]['content'] == 'yes'


@pytest.mark.asyncio
async def test_no_pair_when_target_has_no_prior_context() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=2)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Anton', 'lonely first message', 1700000000), ('Alex', 'hi', 1700000020)])
    await _run_build(uow, storage, export.chat_id)
    datasets = uow.training_dataset.get_all()
    pairs = _decode_jsonl(storage, datasets[0])
    assert pairs == []


@pytest.mark.asyncio
async def test_consecutive_target_messages_are_aggregated_into_one_response() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=10)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Alex', 'how are you?', 1700000000), ('Anton', 'fine', 1700000010), ('Anton', 'and you?', 1700000020)])
    await _run_build(uow, storage, export.chat_id)
    datasets = uow.training_dataset.get_all()
    pairs = _decode_jsonl(storage, datasets[0])
    assert len(pairs) == 1
    assert pairs[0]['messages'][2]['content'] == 'fine\nand you?'


@pytest.mark.asyncio
async def test_target_messages_split_when_gap_exceeds_aggregation_timeout() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=10)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Alex', 'ok?', 1700000000), ('Anton', 'yes', 1700000010), ('Alex', 'later question', 1700000200), ('Anton', 'yep again', 1700000210)])
    await _run_build(uow, storage, export.chat_id)
    datasets = uow.training_dataset.get_all()
    pairs = _decode_jsonl(storage, datasets[0])
    assert len(pairs) == 2
    assert pairs[0]['messages'][2]['content'] == 'yes'
    assert pairs[1]['messages'][2]['content'] == 'yep again'


def _reply_period_from_outbox(uow: InMemoryUnitOfWork) -> int:
    built_events = [e for e in uow.outbox if isinstance(e, TrainingDataset.EventDatasetBuilt)]
    assert len(built_events) == 1, 'exactly one EventDatasetBuilt expected'
    return built_events[0].payload.reply_period


@pytest.mark.asyncio
async def test_reply_period_reflects_target_ratio() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=5)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Alex', '1', 1700000000), ('Alex', '2', 1700000010), ('Alex', '3', 1700000020), ('Alex', '4', 1700000030), ('Anton', '5', 1700000040)])
    await _run_build(uow, storage, export.chat_id)
    assert _reply_period_from_outbox(uow) == 5


@pytest.mark.asyncio
async def test_reply_period_zero_targets_defaults_to_total_messages() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=3)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Alex', '1', 1700000000), ('Alex', '2', 1700000010), ('Alex', '3', 1700000020)])
    await _run_build(uow, storage, export.chat_id)
    assert _reply_period_from_outbox(uow) == 3
    datasets = uow.training_dataset.get_all()
    pairs = _decode_jsonl(storage, datasets[0])
    assert pairs == []


@pytest.mark.asyncio
async def test_idempotent_when_dataset_already_exists() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=3)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Alex', 'hi', 1700000000), ('Anton', 'yo', 1700000010)])
    await _run_build(uow, storage, export.chat_id)
    files_after_first = storage.stored_count()
    await _run_build(uow, storage, export.chat_id)
    datasets = uow.training_dataset.get_all()
    assert len(datasets) == 1
    assert storage.stored_count() == files_after_first


@pytest.mark.asyncio
async def test_serialized_jsonl_carries_openai_chat_schema() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    export = _bootstrap_chat_export(uow, target_user='Anton', n_messages=2)
    _thread_with_messages(uow, chat_id=export.chat_id, messages_spec=[('Alex', 'ping', 1700000000), ('Anton', 'pong', 1700000010)])
    await _run_build(uow, storage, export.chat_id)
    datasets = uow.training_dataset.get_all()
    pairs = _decode_jsonl(storage, datasets[0])
    assert pairs[0]['messages'][0]['role'] == 'system'
    assert pairs[0]['messages'][1]['role'] == 'user'
    assert pairs[0]['messages'][2]['role'] == 'assistant'
