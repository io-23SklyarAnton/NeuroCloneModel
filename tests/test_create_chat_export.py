from io import BytesIO
import pytest
from common.domain.value_objects import OwnerTelegramID, UserName
from data_preparation.application.features import create_chat_export
from data_preparation.domain.entities import ChatExport
from data_preparation.infrastructure.in_memory import InMemoryUnitOfWork
from tests.fakes import InMemoryStorage


def _valid_export_bytes(chat_id: int=7) -> BytesIO:
    payload = '{"id": ' + str(chat_id) + ', "name": "chat", "type": "private_group", "messages": []}'
    return BytesIO(payload.encode('utf-8'))


def _make_handler() -> tuple[create_chat_export.CommandHandler, InMemoryUnitOfWork, InMemoryStorage]:
    uow = InMemoryUnitOfWork()
    storage = InMemoryStorage()
    handler = create_chat_export.CommandHandler(uow=uow, storage=storage)
    return (handler, uow, storage)


@pytest.mark.asyncio
async def test_valid_file_creates_pending_export_and_stores_bytes() -> None:
    handler, uow, storage = _make_handler()
    payload = _valid_export_bytes(chat_id=7)
    response = await handler.handle(create_chat_export.Command(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_bytes=payload))
    assert response.chat_export_id == 7
    assert response.chat_export_file_path == 'chat-exports/7.json'
    stored = await uow.chat_export.get_by_id_optional(ChatExport.ChatID(value=7))
    assert stored is not None
    assert stored.status == ChatExport.Status.PENDING
    assert stored.target_user_name == UserName(value='Anton')
    assert storage.stored_count() == 1


@pytest.mark.asyncio
async def test_invalid_json_does_not_persist() -> None:
    handler, uow, storage = _make_handler()
    bad = BytesIO(b'not a valid json {')
    response = await handler.handle(create_chat_export.Command(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_bytes=bad))
    assert response.chat_export_id is None
    assert 'Invalid' in response.message
    assert storage.stored_count() == 0


@pytest.mark.asyncio
async def test_duplicate_chat_id_returns_existing_path() -> None:
    handler, uow, storage = _make_handler()
    await handler.handle(create_chat_export.Command(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_bytes=_valid_export_bytes(chat_id=7)))
    response = await handler.handle(create_chat_export.Command(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_bytes=_valid_export_bytes(chat_id=7)))
    assert response.chat_export_id == 7
    assert 'already exists' in response.message
    assert storage.stored_count() == 1


@pytest.mark.asyncio
async def test_missing_id_field_is_rejected() -> None:
    handler, _, storage = _make_handler()
    no_id = BytesIO(b'{"name": "chat", "messages": []}')
    response = await handler.handle(create_chat_export.Command(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_bytes=no_id))
    assert response.chat_export_id is None
    assert storage.stored_count() == 0
