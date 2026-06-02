import pytest
from common.domain.value_objects import FileReference, OwnerTelegramID, ReplyPeriod, UserName
from model_engine.domain.entities import NeuroClone


def _dataset_ref() -> FileReference:
    return FileReference(bucket='imitation-datasets', key='42_20260101_000000.jsonl')


def _adapter_ref() -> FileReference:
    return FileReference(bucket='adapters', key='42.safetensors')


def _make_neuroclone() -> NeuroClone:
    return NeuroClone.create(owner_id=OwnerTelegramID(value=42), target_user_name=UserName(value='Anton'), dataset_file_reference=_dataset_ref(), reply_period=ReplyPeriod(value=5))


class TestNeuroCloneCreation:

    def test_create_starts_preparing(self) -> None:
        nc = _make_neuroclone()
        assert nc.status == NeuroClone.Status.PREPARING
        assert nc.is_ready is False
        assert nc.adapter_file_reference is None

    def test_create_emits_event(self) -> None:
        nc = _make_neuroclone()
        queued = nc._events_to_publish
        assert len(queued) == 1
        assert isinstance(queued[0], NeuroClone.EventNeuroCloneCreated)


class TestStatusTransitions:

    def test_start_training_from_preparing(self) -> None:
        nc = _make_neuroclone()
        nc.start_training()
        assert nc.status == NeuroClone.Status.TRAINING

    def test_start_training_twice_raises(self) -> None:
        nc = _make_neuroclone()
        nc.start_training()
        with pytest.raises(NeuroClone.IllegalStateTransitionError):
            nc.start_training()

    def test_set_adapter_requires_training_state(self) -> None:
        nc = _make_neuroclone()
        with pytest.raises(NeuroClone.IllegalStateTransitionError):
            nc.set_adapter_file_reference(_adapter_ref())

    def test_set_adapter_in_training_persists_reference(self) -> None:
        nc = _make_neuroclone()
        nc.start_training()
        nc.set_adapter_file_reference(_adapter_ref())
        assert nc.adapter_file_reference == _adapter_ref()

    def test_set_adapter_twice_raises(self) -> None:
        nc = _make_neuroclone()
        nc.start_training()
        nc.set_adapter_file_reference(_adapter_ref())
        other = FileReference(bucket='adapters', key='other.safetensors')
        with pytest.raises(RuntimeError, match='already set'):
            nc.set_adapter_file_reference(other)


class TestReadyTransition:

    def test_mark_ready_from_preparing_emits_event(self) -> None:
        nc = _make_neuroclone()
        nc.mark_ready()
        assert nc.is_ready is True
        ready_events = [e for e in nc._events_to_publish if isinstance(e, NeuroClone.EventNeuroCloneReady)]
        assert len(ready_events) == 1
        assert ready_events[0].payload.owner_telegram_id == OwnerTelegramID(value=42)
        assert ready_events[0].payload.reply_period == 5

    def test_mark_ready_from_training_emits_event(self) -> None:
        nc = _make_neuroclone()
        nc.start_training()
        nc.mark_ready()
        assert nc.is_ready is True

    def test_mark_ready_from_failed_raises(self) -> None:
        nc = _make_neuroclone()
        nc.mark_failed()
        with pytest.raises(NeuroClone.IllegalStateTransitionError):
            nc.mark_ready()


class TestFailureTransition:

    def test_mark_failed_does_not_require_specific_state(self) -> None:
        nc = _make_neuroclone()
        nc.mark_failed()
        assert nc.status == NeuroClone.Status.FAILED
        assert nc.is_ready is False
