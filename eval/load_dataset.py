import json
from pathlib import Path
from typing import Union

from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.value_objects import ID, DateUnixtime
from infrastructure.in_memory.uow import InMemoryUnitOfWork


def load_irc_dataset_to_memory(
        json_filepath: Union[str, Path],
        uow: InMemoryUnitOfWork,
) -> InMemoryUnitOfWork:
    with open(json_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    user_mapping: dict[str, str] = {}
    for user_data in data.get("members", []):
        user_mapping[user_data["id"]] = user_data["name"]

    chat_counter = 1
    msg_counter = 1

    for channel_data in data.get("channels", []):
        messages_data = channel_data.get("messages", [])

        chat_ext_id = Chat.ExternalID(value=chat_counter)
        chat_counter += 1

        chat = Chat(
            external_id=chat_ext_id,
            n_messages=len(messages_data),
        )

        uow.chat.create(
            aggregate=chat,
        )

        sorted_messages = sorted(
            messages_data,
            key=lambda x: int(x["timestamp"]),
        )

        for seq_num, msg_data in enumerate(sorted_messages, 1):
            author_name = user_mapping.get(msg_data["authorId"], "UnknownUser")

            msg_ext_id = Message.ExternalID(value=msg_counter)
            msg_counter += 1

            message = Message(
                id_=ID.create(),
                external_id=msg_ext_id,
                reply_to_message_id=None,
                sequence_number=Message.SequenceNumber(value=seq_num),
                date_unixtime=DateUnixtime(value=int(msg_data["timestamp"])),
                from_user=Message.UserName(value=author_name),
                text=Message.Text(value=msg_data["content"]),
                chat_id=chat_ext_id,
                thread_id=None,
            )

            setattr(message, "expected_thread_id", msg_data["conversation"])

            uow.message.create(message)

    return uow
