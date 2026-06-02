import uuid
import pytest
from common.domain.value_objects import FileReference, OwnerTelegramID, ReplyPeriod, UserName
from bot_operations.application.features import assign_neuroclone_to_bot, neuroclone_assigned, neuroclone_ready, run_bot
from bot_operations.domain.entities import Bot
from data_preparation.application.features import build_imitation_dataset, chat_export_created, chat_export_ingested, chat_export_ready, ingest_chat_export, process_chat_threads
from data_preparation.domain.entities import ChatExport, TrainingDataset
from model_engine.application.features import create_neuroclone, dataset_built, neuroclone_created, train_lora_adapter
from model_engine.domain.entities import NeuroClone
from tests.fakes import InMemoryEventBus


@pytest.mark.asyncio
async def test_chat_export_created_triggers_ingest_with_chat_id() -> None:
    bus = InMemoryEventBus()
    handler = chat_export_created.EventHandler(bus=bus)
    event = ChatExport.EventChatExportCreated(object_id='7', payload=ChatExport.EventChatExportCreated.Payload(file_reference=FileReference(bucket='chat-exports', key='7.json')))
    await handler.handle(event)
    cmds = bus.commands_of_type(ingest_chat_export.Command)
    assert len(cmds) == 1
    assert cmds[0].chat_export_id == ChatExport.ChatID(value=7)


@pytest.mark.asyncio
async def test_chat_export_ingested_triggers_thread_processing() -> None:
    bus = InMemoryEventBus()
    handler = chat_export_ingested.EventHandler(bus=bus)
    event = ChatExport.EventChatExportIngested(object_id='7')
    await handler.handle(event)
    cmds = bus.commands_of_type(process_chat_threads.Command)
    assert len(cmds) == 1
    assert cmds[0].chat_export_id == ChatExport.ChatID(value=7)


@pytest.mark.asyncio
async def test_chat_export_ready_triggers_dataset_build() -> None:
    bus = InMemoryEventBus()
    handler = chat_export_ready.EventHandler(bus=bus)
    event = ChatExport.EventChatExportReady(object_id='7')
    await handler.handle(event)
    cmds = bus.commands_of_type(build_imitation_dataset.Command)
    assert len(cmds) == 1
    assert cmds[0].chat_export_id == ChatExport.ChatID(value=7)


@pytest.mark.asyncio
async def test_dataset_built_triggers_neuroclone_creation_with_full_payload() -> None:
    bus = InMemoryEventBus()
    handler = dataset_built.EventHandler(bus=bus)
    dataset_id = str(uuid.uuid4())
    event = TrainingDataset.EventDatasetBuilt(object_id=dataset_id, payload=TrainingDataset.EventDatasetBuilt.Payload(owner_telegram_id=42, target_user_name='Anton', file_reference=FileReference(bucket='imitation-datasets', key='7.jsonl'), source_chat_export_id=7, n_pairs=123, reply_period=5))
    await handler.handle(event)
    cmds = bus.commands_of_type(create_neuroclone.Command)
    assert len(cmds) == 1
    cmd = cmds[0]
    assert cmd.owner_id == OwnerTelegramID(value=42)
    assert cmd.target_user_name == UserName(value='Anton')
    assert cmd.reply_period == ReplyPeriod(value=5)
    assert cmd.dataset_file_reference == FileReference(bucket='imitation-datasets', key='7.jsonl')


@pytest.mark.asyncio
async def test_neuroclone_created_triggers_training() -> None:
    bus = InMemoryEventBus()
    handler = neuroclone_created.EventHandler(bus=bus)
    nc_id = uuid.uuid4()
    event = NeuroClone.EventNeuroCloneCreated(object_id=str(nc_id))
    await handler.handle(event)
    cmds = bus.commands_of_type(train_lora_adapter.Command)
    assert len(cmds) == 1
    assert cmds[0].neuroclone_id.value == nc_id


@pytest.mark.asyncio
async def test_neuroclone_ready_triggers_assign_to_bot() -> None:
    bus = InMemoryEventBus()
    handler = neuroclone_ready.EventHandler(bus=bus)
    nc_id = uuid.uuid4()
    event = NeuroClone.EventNeuroCloneReady(object_id=str(nc_id), payload=NeuroClone.EventNeuroCloneReady.Payload(owner_telegram_id=OwnerTelegramID(value=42), reply_period=8))
    await handler.handle(event)
    cmds = bus.commands_of_type(assign_neuroclone_to_bot.Command)
    assert len(cmds) == 1
    cmd = cmds[0]
    assert cmd.owner_id == OwnerTelegramID(value=42)
    assert cmd.neuroclone_id.value == nc_id
    assert cmd.reply_period == ReplyPeriod(value=8)


@pytest.mark.asyncio
async def test_neuroclone_assigned_triggers_run_bot() -> None:
    bus = InMemoryEventBus()
    handler = neuroclone_assigned.EventHandler(bus=bus)
    bot_id = uuid.uuid4()
    event = Bot.NeuroCloneAssigned(object_id=str(bot_id))
    await handler.handle(event)
    cmds = bus.commands_of_type(run_bot.Command)
    assert len(cmds) == 1
    assert cmds[0].bot_id.value == bot_id
