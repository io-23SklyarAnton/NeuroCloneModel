import pytest
from bot_operations.domain.entities import Bot
from common.domain.value_objects import ID, OwnerTelegramID, ReplyPeriod


def _make_bot() -> Bot:
    return Bot.create(owner_id=OwnerTelegramID(value=42), token=Bot.Token(value='token-42:abc'), name=Bot.Name(value='TestBot'))


class TestBotCreation:

    def test_create_starts_in_pending_status(self) -> None:
        bot = _make_bot()
        assert bot.status == Bot.BotStatus.PENDING
        assert bot.is_running is False
        assert bot.neuroclone_id is None
        assert bot.reply_period is None

    def test_create_emits_event(self) -> None:
        bot = _make_bot()
        events = list(bot.collected_events_for_test()) if hasattr(bot, 'collected_events_for_test') else None
        queued = bot._events_to_publish
        assert len(queued) == 1
        assert isinstance(queued[0], Bot.EventBotCreated)
        assert queued[0].payload.owner_telegram_id == 42
        assert queued[0].payload.bot_name == 'TestBot'


class TestNeuroCloneAssignment:

    def test_assign_neuroclone_persists_link(self) -> None:
        bot = _make_bot()
        neuroclone_id = ID.create()
        bot.assign_neuroclone(neuroclone_id=neuroclone_id, reply_period=ReplyPeriod(value=7))
        assert bot.neuroclone_id == neuroclone_id
        assert bot.reply_period == ReplyPeriod(value=7)

    def test_assign_neuroclone_twice_fails(self) -> None:
        bot = _make_bot()
        bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=3))
        with pytest.raises(RuntimeError, match='already has a neuroclone'):
            bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=10))


class TestBotLifecycle:

    def test_start_without_neuroclone_raises(self) -> None:
        bot = _make_bot()
        with pytest.raises(Bot.NeuroCloneNotReadyError):
            bot.start_bot()

    def test_start_after_assignment_transitions_to_running(self) -> None:
        bot = _make_bot()
        bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=5))
        bot.start_bot()
        assert bot.status == Bot.BotStatus.RUNNING
        assert bot.is_running is True

    def test_start_when_already_running_raises(self) -> None:
        bot = _make_bot()
        bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=5))
        bot.start_bot()
        with pytest.raises(Bot.IllegalStateTransitionError):
            bot.start_bot()

    def test_stop_when_not_running_raises(self) -> None:
        bot = _make_bot()
        with pytest.raises(Bot.IllegalStateTransitionError):
            bot.stop_bot()

    def test_stop_after_start_transitions_to_stopped(self) -> None:
        bot = _make_bot()
        bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=5))
        bot.start_bot()
        bot.stop_bot()
        assert bot.status == Bot.BotStatus.STOPPED
        assert bot.is_running is False


class TestOwnership:

    def test_owner_matches_creation_id(self) -> None:
        bot = _make_bot()
        bot.ensure_owned_by(OwnerTelegramID(value=42))

    def test_non_owner_raises(self) -> None:
        bot = _make_bot()
        with pytest.raises(Bot.NotOwnedError):
            bot.ensure_owned_by(OwnerTelegramID(value=999))
