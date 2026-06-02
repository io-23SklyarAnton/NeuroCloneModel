import pytest
from bot_operations.application.features import receive_chat_message
from bot_operations.domain.entities import Bot, LiveChat, LiveMessage
from bot_operations.infrastructure.in_memory import InMemoryUnitOfWork
from common.domain.value_objects import ID, OwnerTelegramID, ReplyPeriod, UserName
from tests.fakes import StubPersonaReplyService


def _register_bot_with_neuroclone(uow: InMemoryUnitOfWork, reply_period: int=1) -> Bot:
    bot = Bot.create(owner_id=OwnerTelegramID(value=42), token=Bot.Token(value='t:abc'), name=Bot.Name(value='TestBot'))
    bot.assign_neuroclone(neuroclone_id=ID.create(), reply_period=ReplyPeriod(value=reply_period))
    uow.bot.create(bot)
    return bot


def _cmd(bot_id: ID, chat_id: int=1234, text: str='hi', force_reply: bool=False, from_user: str='Alex') -> receive_chat_message.Command:
    return receive_chat_message.Command(bot_id=bot_id, chat_external_id=LiveChat.ExternalID(value=chat_id), user_name=UserName(value=from_user), text=LiveMessage.Text(value=text), force_reply=force_reply)


@pytest.mark.asyncio
async def test_new_chat_with_force_reply_creates_chat_and_persists_reply() -> None:
    uow = InMemoryUnitOfWork()
    bot = _register_bot_with_neuroclone(uow)
    persona = StubPersonaReplyService(canned_reply='hello back')
    handler = receive_chat_message.CommandHandler(uow=uow, persona_reply_service=persona)
    response = await handler.handle(_cmd(bot.id, force_reply=True))
    assert response.reply_text == 'hello back'
    stored_chat = await uow.live_chat.get_by_id_optional(LiveChat.ExternalID(value=1234))
    assert stored_chat is not None
    assert len(stored_chat.recent_messages) == 2
    assert stored_chat.recent_messages[0].is_from_bot is False
    assert stored_chat.recent_messages[1].is_from_bot is True
    assert stored_chat.recent_messages[1].text == LiveMessage.Text(value='hello back')


@pytest.mark.asyncio
async def test_bot_without_neuroclone_never_replies() -> None:
    uow = InMemoryUnitOfWork()
    bot = Bot.create(owner_id=OwnerTelegramID(value=42), token=Bot.Token(value='t:abc'), name=Bot.Name(value='Empty'))
    uow.bot.create(bot)
    persona = StubPersonaReplyService(canned_reply='should-never-be-called')
    handler = receive_chat_message.CommandHandler(uow=uow, persona_reply_service=persona)
    response = await handler.handle(_cmd(bot.id, force_reply=True))
    assert response.reply_text is None
    assert persona.call_count() == 0
    stored_chat = await uow.live_chat.get_by_id_optional(LiveChat.ExternalID(value=1234))
    assert stored_chat is not None
    assert len(stored_chat.recent_messages) == 1


@pytest.mark.asyncio
async def test_persona_returning_none_does_not_append_bot_message() -> None:
    uow = InMemoryUnitOfWork()
    bot = _register_bot_with_neuroclone(uow)
    persona = StubPersonaReplyService(canned_reply=None)
    handler = receive_chat_message.CommandHandler(uow=uow, persona_reply_service=persona)
    response = await handler.handle(_cmd(bot.id, force_reply=True))
    assert response.reply_text is None
    stored_chat = await uow.live_chat.get_by_id_optional(LiveChat.ExternalID(value=1234))
    assert stored_chat is not None
    assert len(stored_chat.recent_messages) == 1


@pytest.mark.asyncio
async def test_existing_chat_is_updated_not_recreated() -> None:
    uow = InMemoryUnitOfWork()
    bot = _register_bot_with_neuroclone(uow)
    persona = StubPersonaReplyService(canned_reply='reply')
    handler = receive_chat_message.CommandHandler(uow=uow, persona_reply_service=persona)
    await handler.handle(_cmd(bot.id, force_reply=True, text='first'))
    await handler.handle(_cmd(bot.id, force_reply=True, text='second'))
    stored_chat = await uow.live_chat.get_by_id_optional(LiveChat.ExternalID(value=1234))
    assert stored_chat is not None
    assert len(stored_chat.recent_messages) == 4
    texts = [m.text.value for m in stored_chat.recent_messages]
    assert texts == ['first', 'reply', 'second', 'reply']


@pytest.mark.asyncio
async def test_reply_period_one_with_force_disabled_still_replies_eventually() -> None:
    uow = InMemoryUnitOfWork()
    bot = _register_bot_with_neuroclone(uow, reply_period=1)
    persona = StubPersonaReplyService(canned_reply='r')
    handler = receive_chat_message.CommandHandler(uow=uow, persona_reply_service=persona)
    response = await handler.handle(_cmd(bot.id, force_reply=False))
    assert response.reply_text == 'r'


@pytest.mark.asyncio
async def test_persona_receives_full_context() -> None:
    uow = InMemoryUnitOfWork()
    bot = _register_bot_with_neuroclone(uow)
    persona = StubPersonaReplyService(canned_reply='hi')
    handler = receive_chat_message.CommandHandler(uow=uow, persona_reply_service=persona)
    await handler.handle(_cmd(bot.id, force_reply=True, text='ping', from_user='Alex'))
    assert persona.call_count() == 1
    _, ctx = persona.calls[0]
    assert len(ctx) == 1
    assert ctx[0].sender == 'Alex'
    assert ctx[0].text == 'ping'
