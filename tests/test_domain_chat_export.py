import pytest
from common.domain.value_objects import FileReference, OwnerTelegramID, UserName
from data_preparation.domain.entities import ChatExport


def _make_chat_export(chat_id: int=7) -> ChatExport:
    return ChatExport.create(chat_id=ChatExport.ChatID(value=chat_id), owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), file_reference=FileReference(bucket='chat-exports', key=f'{chat_id}.json'))


class TestChatExportCreation:

    def test_create_starts_pending(self) -> None:
        export = _make_chat_export()
        assert export.status == ChatExport.Status.PENDING
        assert export.n_messages == 0

    def test_create_emits_event_with_file_reference(self) -> None:
        export = _make_chat_export(chat_id=7)
        queued = export._events_to_publish
        assert len(queued) == 1
        assert isinstance(queued[0], ChatExport.EventChatExportCreated)
        assert queued[0].payload.file_reference == FileReference(bucket='chat-exports', key='7.json')


class TestIngestionTransition:

    def test_mark_ingested_from_pending(self) -> None:
        export = _make_chat_export()
        export.record_message_count(123)
        export.mark_ingested()
        assert export.status == ChatExport.Status.INGESTED
        assert export.n_messages == 123

    def test_mark_ingested_twice_raises(self) -> None:
        export = _make_chat_export()
        export.mark_ingested()
        with pytest.raises(ChatExport.IllegalStateTransitionError):
            export.mark_ingested()

    def test_mark_ingested_emits_event(self) -> None:
        export = _make_chat_export()
        export.mark_ingested()
        ingested_events = [e for e in export._events_to_publish if isinstance(e, ChatExport.EventChatExportIngested)]
        assert len(ingested_events) == 1


class TestReadyTransition:

    def test_mark_ready_requires_ingested(self) -> None:
        export = _make_chat_export()
        with pytest.raises(ChatExport.IllegalStateTransitionError):
            export.mark_ready()

    def test_mark_ready_from_ingested(self) -> None:
        export = _make_chat_export()
        export.mark_ingested()
        export.mark_ready()
        assert export.status == ChatExport.Status.READY

    def test_mark_ready_emits_event(self) -> None:
        export = _make_chat_export()
        export.mark_ingested()
        export.mark_ready()
        ready_events = [e for e in export._events_to_publish if isinstance(e, ChatExport.EventChatExportReady)]
        assert len(ready_events) == 1


class TestFailureTransition:

    def test_mark_failed_from_pending(self) -> None:
        export = _make_chat_export()
        export.mark_failed()
        assert export.status == ChatExport.Status.FAILED

    def test_mark_failed_from_ingested(self) -> None:
        export = _make_chat_export()
        export.mark_ingested()
        export.mark_failed()
        assert export.status == ChatExport.Status.FAILED
