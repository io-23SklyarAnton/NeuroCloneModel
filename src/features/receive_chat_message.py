__all__ = [
    "Command",
    "CommandHandler",
]

from typing import Optional

from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.value_objects import ID, DateUnixtime
from features import interfaces
from features.base import ICommand


class Command(ICommand):
    chat_external_id: Chat.ExternalID
    message_external_id: Message.ExternalID
    reply_to_message_external_id: Optional[Message.ExternalID]
    from_user: Message.UserName
    text: Message.Text
    date_unixtime: DateUnixtime
    message_type: Message.Type


class CommandHandler:
    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def handle(
            self,
            command: Command,
    ) -> None:
        chat: Chat = await self._get_or_create_chat(command.chat_external_id)
        reply_to_message_id: Optional[ID] = await self._resolve_reply_to(
            chat_external_id=command.chat_external_id,
            reply_to_message_external_id=command.reply_to_message_external_id,
        )

        chat.register_new_message()
        message = Message.create(
            external_id=command.message_external_id,
            reply_to_message_id=reply_to_message_id,
            sequence_number=Message.SequenceNumber(value=chat.n_messages),
            date_unixtime=command.date_unixtime,
            from_user=command.from_user,
            text=command.text,
            chat_id=chat.external_id,
            message_type=command.message_type,
        )

        self._uow.message.create(message)
        self._uow.chat.update(chat)
        self._uow.commit()

    async def _get_or_create_chat(
            self,
            chat_external_id: Chat.ExternalID,
    ) -> Chat:
        existing_chat: Optional[Chat] = await self._uow.chat.get_by_id_optional(chat_external_id)
        if existing_chat is not None:
            return existing_chat

        new_chat = Chat.create(
            external_id=chat_external_id,
            n_messages=0,
        )
        self._uow.chat.create(new_chat)

        return new_chat

    async def _resolve_reply_to(
            self,
            chat_external_id: Chat.ExternalID,
            reply_to_message_external_id: Optional[Message.ExternalID],
    ) -> Optional[ID]:
        if reply_to_message_external_id is None:
            return None

        replied_message: Optional[Message] = await self._uow.message.get_by_chat_and_external_id_optional(
            chat_id=chat_external_id,
            external_id=reply_to_message_external_id,
        )
        if replied_message is None:
            return None

        return replied_message.id
