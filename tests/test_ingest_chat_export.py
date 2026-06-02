import json
from io import BytesIO
import pytest
from common.domain.value_objects import FileReference, OwnerTelegramID, UserName
from data_preparation.application.features import ingest_chat_export
from data_preparation.domain.entities import ChatExport, ParsedMessage
from data_preparation.infrastructure.in_memory import InMemoryUnitOfWork
from tests.fakes import InMemoryStorage


def _bootstrap_chat_export(uow: InMemoryUnitOfWork, storage: InMemoryStorage, raw_messages: list[dict], chat_id: int=7) -> ChatExport.ChatID:
    file_reference = FileReference(bucket='chat-exports', key=f'{chat_id}.json')
    storage.put(file_reference, json.dumps({'messages': raw_messages}).encode('utf-8'))
    export = ChatExport.create(chat_id=ChatExport.ChatID(value=chat_id), owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_reference=file_reference)
    uow.chat_export.create(export)
    return export.chat_id


async def _run_ingest(uow: InMemoryUnitOfWork, storage: InMemoryStorage, chat_id: ChatExport.ChatID) -> None:
    handler = ingest_chat_export.CommandHandler(uow=uow, storage=storage)
    await handler.handle(ingest_chat_export.Command(chat_export_id=chat_id))


def _simple_text_message(msg_id: int, text: str, from_user: str='Alex', date: int=1700000000) -> dict:
    return {'id': msg_id, 'type': 'message', 'date_unixtime': str(date), 'from': from_user, 'from_id': f'user{from_user}', 'text': text}


@pytest.mark.asyncio
async def test_basic_text_messages_are_persisted_in_order() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[_simple_text_message(1, 'hello', from_user='Alex', date=1700000000), _simple_text_message(2, 'hi', from_user='Anton', date=1700000020), _simple_text_message(3, 'how are you?', from_user='Alex', date=1700000040)])
    await _run_ingest(uow, storage, chat_id)
    refreshed = await uow.chat_export.get_by_id_or_raise(chat_id)
    assert refreshed.status == ChatExport.Status.INGESTED
    assert refreshed.n_messages == 3
    messages = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=chat_id, offset=0, limit=100)
    assert [m.text.value for m in messages] == ['hello', 'hi', 'how are you?']
    assert [m.sequence_number.value for m in messages] == [1, 2, 3]


@pytest.mark.asyncio
async def test_messages_without_from_are_skipped() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[_simple_text_message(1, 'kept', from_user='Alex'), {'id': 2, 'type': 'message', 'date_unixtime': '1700000010', 'text': 'no author'}, _simple_text_message(3, 'kept2', from_user='Alex', date=1700000020)])
    await _run_ingest(uow, storage, chat_id)
    messages = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=chat_id, offset=0, limit=100)
    assert [m.text.value for m in messages] == ['kept', 'kept2']


@pytest.mark.asyncio
async def test_service_messages_are_persisted_with_action_prefix() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[{'id': 1, 'type': 'service', 'date_unixtime': '1700000000', 'actor': 'Alex', 'actor_id': 'userAlex', 'action': 'pin_message'}, _simple_text_message(2, 'ok', from_user='Anton')])
    await _run_ingest(uow, storage, chat_id)
    messages = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=chat_id, offset=0, limit=100)
    assert messages[0].text.value == '[SERVICE pin_message]'
    assert messages[0].message_type == ParsedMessage.Type.SERVICE
    assert messages[1].text.value == 'ok'
    assert messages[1].message_type == ParsedMessage.Type.TEXT


@pytest.mark.asyncio
async def test_sticker_media_yields_sticker_prefix() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[{'id': 1, 'type': 'message', 'date_unixtime': '1700000000', 'from': 'Alex', 'from_id': 'userAlex', 'media_type': 'sticker', 'sticker_emoji': '🔥', 'text': ''}])
    await _run_ingest(uow, storage, chat_id)
    messages = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=chat_id, offset=0, limit=100)
    assert messages[0].text.value == '[STICKER 🔥]'
    assert messages[0].message_type == ParsedMessage.Type.STICKER


@pytest.mark.asyncio
async def test_formatted_text_array_is_concatenated() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[{'id': 1, 'type': 'message', 'date_unixtime': '1700000000', 'from': 'Alex', 'from_id': 'userAlex', 'text': ['Hello, ', {'type': 'bold', 'text': 'world'}, '!']}])
    await _run_ingest(uow, storage, chat_id)
    messages = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=chat_id, offset=0, limit=100)
    assert messages[0].text.value == 'Hello, world!'


@pytest.mark.asyncio
async def test_internal_reply_links_resolve_to_parent_id() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[_simple_text_message(100, 'question?', from_user='Alex'), {'id': 101, 'type': 'message', 'date_unixtime': '1700000010', 'from': 'Anton', 'from_id': 'userAnton', 'reply_to_message_id': 100, 'text': 'answer'}])
    await _run_ingest(uow, storage, chat_id)
    messages = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=chat_id, offset=0, limit=100)
    parent = messages[0]
    reply = messages[1]
    assert reply.reply_to_message_id == parent.id


@pytest.mark.asyncio
async def test_cross_chat_reply_is_dropped() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[{'id': 1, 'type': 'message', 'date_unixtime': '1700000000', 'from': 'Anton', 'from_id': 'userAnton', 'reply_to_message_id': 999, 'reply_to_peer_id': 'channel123', 'text': 'stranded reply'}])
    await _run_ingest(uow, storage, chat_id)
    messages = await uow.parsed_message.get_batch_by_chat_export_id(chat_export_id=chat_id, offset=0, limit=100)
    assert messages[0].reply_to_message_id is None


@pytest.mark.asyncio
async def test_running_twice_skips_on_non_pending_status() -> None:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    chat_id = _bootstrap_chat_export(uow, storage, raw_messages=[_simple_text_message(1, 'hi', from_user='Alex')])
    await _run_ingest(uow, storage, chat_id)
    await _run_ingest(uow, storage, chat_id)
    refreshed = await uow.chat_export.get_by_id_or_raise(chat_id)
    assert refreshed.status == ChatExport.Status.INGESTED
    assert refreshed.n_messages == 1
