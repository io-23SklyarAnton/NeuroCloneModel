import pytest
from common.domain.value_objects import FileReference, ID, OwnerTelegramID, UserName
from data_preparation.application.features import process_chat_threads
from data_preparation.domain.entities import ChatExport, ParsedMessage, Thread
from data_preparation.domain.value_objects import DateUnixtime
from data_preparation.infrastructure.in_memory import InMemoryUnitOfWork
from tests.fakes import StubInferenceEngine


def _ingested_export(uow: InMemoryUnitOfWork, target_user: str='Anton', n_messages: int=0, chat_id: int=7) -> ChatExport:
    export = ChatExport.create(chat_id=ChatExport.ChatID(value=chat_id), owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value=target_user), file_reference=FileReference(bucket='chat-exports', key=f'{chat_id}.json'))
    export.record_message_count(n_messages)
    export.mark_ingested()
    uow.chat_export.create(export)
    return export


def _persist_message(uow: InMemoryUnitOfWork, chat_id: ChatExport.ChatID, seq: int, from_user: str, text: str='msg', date: int=1700000000, reply_to: ID | None=None) -> ParsedMessage:
    msg = ParsedMessage.create(external_id=ParsedMessage.ExternalID(value=seq), reply_to_message_id=reply_to, sequence_number=ParsedMessage.SequenceNumber(value=seq), date_unixtime=DateUnixtime(value=date), from_user=UserName(value=from_user), text=ParsedMessage.Text(value=text), chat_export_id=chat_id, message_type=ParsedMessage.Type.TEXT)
    uow.parsed_message.create(msg)
    return msg


@pytest.mark.asyncio
async def test_skip_when_chat_export_is_not_ingested() -> None:
    uow = InMemoryUnitOfWork()
    engine = StubInferenceEngine()
    export = ChatExport.create(chat_id=ChatExport.ChatID(value=7), owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_reference=FileReference(bucket='chat-exports', key='7.json'))
    uow.chat_export.create(export)
    handler = process_chat_threads.CommandHandler(uow=uow, inference_engine=engine)
    await handler.handle(process_chat_threads.Command(chat_export_id=export.chat_id))
    refreshed = await uow.chat_export.get_by_id_or_raise(export.chat_id)
    assert refreshed.status == ChatExport.Status.PENDING
    assert engine.generate_calls == []


@pytest.mark.asyncio
async def test_export_without_target_user_is_marked_failed() -> None:
    uow = InMemoryUnitOfWork()
    engine = StubInferenceEngine()
    export = _ingested_export(uow, target_user='Ghost', n_messages=0)
    handler = process_chat_threads.CommandHandler(uow=uow, inference_engine=engine)
    await handler.handle(process_chat_threads.Command(chat_export_id=export.chat_id))
    refreshed = await uow.chat_export.get_by_id_or_raise(export.chat_id)
    assert refreshed.status == ChatExport.Status.FAILED
    assert engine.generate_calls == []


@pytest.mark.asyncio
async def test_happy_path_creates_threads_and_marks_ready() -> None:
    uow = InMemoryUnitOfWork()
    engine = StubInferenceEngine(default_response='0')
    export = _ingested_export(uow, target_user='Anton', n_messages=3)
    _persist_message(uow, export.chat_id, seq=1, from_user='Alex', text='hello', date=1700000000)
    _persist_message(uow, export.chat_id, seq=2, from_user='Anton', text='hi', date=1700000060)
    _persist_message(uow, export.chat_id, seq=3, from_user='Alex', text='how are you?', date=1700000120)
    handler = process_chat_threads.CommandHandler(uow=uow, inference_engine=engine)
    await handler.handle(process_chat_threads.Command(chat_export_id=export.chat_id))
    refreshed = await uow.chat_export.get_by_id_or_raise(export.chat_id)
    assert refreshed.status == ChatExport.Status.READY
    threads = await uow.thread.get_all_by_chat_export_id(export.chat_id)
    assert len(threads) >= 1
    persisted = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=export.chat_id, offset=0, limit=100)
    assigned = [m for m in persisted if m.thread_id is not None]
    assert len(assigned) == 3


@pytest.mark.asyncio
async def test_explicit_reply_link_assigns_to_parent_thread_without_calling_llm() -> None:
    uow = InMemoryUnitOfWork()
    engine = StubInferenceEngine(default_response='0')
    export = _ingested_export(uow, target_user='Anton', n_messages=3)
    parent = _persist_message(uow, export.chat_id, seq=1, from_user='Alex', text='question', date=1700000000)
    _persist_message(uow, export.chat_id, seq=2, from_user='Anton', text='answer', date=1700000050, reply_to=parent.id)
    _persist_message(uow, export.chat_id, seq=3, from_user='Alex', text='thanks', date=1700000100)
    handler = process_chat_threads.CommandHandler(uow=uow, inference_engine=engine)
    await handler.handle(process_chat_threads.Command(chat_export_id=export.chat_id))
    persisted = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=export.chat_id, offset=0, limit=100)
    parent_after = next((m for m in persisted if m.sequence_number.value == 1))
    reply_after = next((m for m in persisted if m.sequence_number.value == 2))
    assert parent_after.thread_id is not None
    assert reply_after.thread_id == parent_after.thread_id


@pytest.mark.asyncio
async def test_fast_track_routes_short_reply_to_most_recent_thread() -> None:
    uow = InMemoryUnitOfWork()
    engine = StubInferenceEngine(default_response='0')
    export = _ingested_export(uow, target_user='Anton', n_messages=4)
    _persist_message(uow, export.chat_id, seq=1, from_user='Alex', text='anyone there?', date=1700000000)
    _persist_message(uow, export.chat_id, seq=2, from_user='Anton', text='yes hi how is it going', date=1700000010)
    _persist_message(uow, export.chat_id, seq=3, from_user='Alex', text='ok', date=1700000030)
    _persist_message(uow, export.chat_id, seq=4, from_user='Anton', text='goodbye', date=1700000040)
    handler = process_chat_threads.CommandHandler(uow=uow, inference_engine=engine)
    await handler.handle(process_chat_threads.Command(chat_export_id=export.chat_id))
    persisted = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=export.chat_id, offset=0, limit=100)
    msg2 = next((m for m in persisted if m.sequence_number.value == 2))
    msg3 = next((m for m in persisted if m.sequence_number.value == 3))
    assert msg3.thread_id == msg2.thread_id


@pytest.mark.asyncio
async def test_llm_decision_routes_to_existing_thread() -> None:
    uow = InMemoryUnitOfWork()
    engine = StubInferenceEngine()
    engine.script_responses(['1', '1'])
    export = _ingested_export(uow, target_user='Anton', n_messages=3)
    _persist_message(uow, export.chat_id, seq=1, from_user='Alex', text='hello hi sup ok', date=1700000000)
    _persist_message(uow, export.chat_id, seq=2, from_user='Anton', text='hi there friend how are you', date=1700000010)
    _persist_message(uow, export.chat_id, seq=3, from_user='Alex', text='great weather today innit', date=1700000200)
    handler = process_chat_threads.CommandHandler(uow=uow, inference_engine=engine)
    await handler.handle(process_chat_threads.Command(chat_export_id=export.chat_id))
    persisted = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=export.chat_id, offset=0, limit=100)
    threads = await uow.thread.get_all_by_chat_export_id(export.chat_id)
    thread_ids = {m.thread_id for m in persisted if m.thread_id is not None}
    assert len(threads) == 1
    assert len(thread_ids) == 1
    assert len(engine.generate_calls) == 2
