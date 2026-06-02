from datetime import datetime, timezone
from bot_operations.domain.entities import LiveChat, LiveMessage
from common.domain.value_objects import ID, UserName


def _make_chat() -> LiveChat:
    return LiveChat.create(external_id=LiveChat.ExternalID(value=1234), bot_id=ID.create())


def _user_msg(text: str, who: str='Alex') -> LiveMessage:
    return LiveMessage.create_user_message(from_user=UserName(value=who), text=LiveMessage.Text(value=text), sent_at=datetime.now(tz=timezone.utc))


def _bot_msg(text: str, who: str='Bot') -> LiveMessage:
    return LiveMessage.create_bot_message(from_user=UserName(value=who), text=LiveMessage.Text(value=text), sent_at=datetime.now(tz=timezone.utc))


class TestLiveChatCreation:

    def test_starts_empty(self) -> None:
        chat = _make_chat()
        assert chat.recent_messages == []
        assert chat.count_messages_since_last_bot_reply() == 0


class TestAppendAndOrdering:

    def test_append_preserves_order(self) -> None:
        chat = _make_chat()
        m1 = _user_msg('first')
        m2 = _user_msg('second')
        m3 = _bot_msg('reply')
        chat.append_message(m1)
        chat.append_message(m2)
        chat.append_message(m3)
        assert chat.recent_messages == [m1, m2, m3]


class TestCountSinceLastBotReply:

    def test_no_bot_reply_yet_counts_all(self) -> None:
        chat = _make_chat()
        chat.append_message(_user_msg('a'))
        chat.append_message(_user_msg('b'))
        chat.append_message(_user_msg('c'))
        assert chat.count_messages_since_last_bot_reply() == 3

    def test_bot_reply_resets_count(self) -> None:
        chat = _make_chat()
        chat.append_message(_user_msg('a'))
        chat.append_message(_user_msg('b'))
        chat.append_message(_bot_msg('reply'))
        assert chat.count_messages_since_last_bot_reply() == 0

    def test_count_resumes_after_bot_reply(self) -> None:
        chat = _make_chat()
        chat.append_message(_user_msg('a'))
        chat.append_message(_bot_msg('reply'))
        chat.append_message(_user_msg('b'))
        chat.append_message(_user_msg('c'))
        assert chat.count_messages_since_last_bot_reply() == 2


class TestLiveMessageFactory:

    def test_user_message_flag(self) -> None:
        msg = _user_msg('hi')
        assert msg.is_from_bot is False
        assert msg.from_user == UserName(value='Alex')

    def test_bot_message_flag(self) -> None:
        msg = _bot_msg('hi')
        assert msg.is_from_bot is True
