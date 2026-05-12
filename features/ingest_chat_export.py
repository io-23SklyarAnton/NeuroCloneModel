import json
from dataclasses import dataclass
from typing import Optional

from domain.entities.chat import Chat
from domain.entities.message import Message
from domain.value_objects import ID, DateUnixtime
from features import interfaces
from features.base import ICommand
from features.interfaces import IStorage

_ExternalIdMap = dict[int, ID]


class Command(ICommand):
    bucket_name: str
    file_name: str


class CommandHandler:
    @dataclass
    class ParsedExport:
        chat: Chat
        messages: list[Message]

    def __init__(
            self,
            uow: interfaces.IUnitOfWork,
            storage: IStorage,
    ) -> None:
        self._uow = uow
        self._storage = storage

    async def handle(
            self,
            command: Command,
    ) -> None:
        raw_json = self._storage.load(
            bucket_name=command.bucket_name,
            file_name=command.file_name,
        )
        data = json.loads(raw_json)
        parsed_export = self._parse_export(data)
        self._persist(parsed_export)

    def _parse_export(
            self,
            data: dict,
    ) -> ParsedExport:
        chat_external_id = Chat.ExternalID(value=data["id"])

        messages = self._parse_messages(
            raw_messages=data["messages"],
            chat_id=chat_external_id,
        )
        chat = Chat.create(
            external_id=chat_external_id,
            n_messages=len(messages),
        )
        return CommandHandler.ParsedExport(
            chat=chat,
            messages=messages,
        )

    def _parse_messages(
            self,
            raw_messages: list[dict],
            chat_id: Chat.ExternalID,
    ) -> list[Message]:
        external_id_map: _ExternalIdMap = {}
        messages: list[Message] = []

        for raw in raw_messages:
            message: Optional[Message] = self._try_parse_message(
                raw=raw,
                sequence_number=len(messages) + 1,
                chat_id=chat_id,
                external_id_map=external_id_map,
            )
            if message is None:
                continue

            external_id_map[raw["id"]] = message.id
            messages.append(message)

        return messages

    def _try_parse_message(
            self,
            raw: dict,
            sequence_number: int,
            chat_id: Chat.ExternalID,
            external_id_map: _ExternalIdMap,
    ) -> Optional[Message]:
        if raw.get("type") != "message":
            return None
        if not raw.get("from"):
            return None

        text = self._extract_text(raw.get("text", ""))
        if not text:
            return None

        return Message.create(
            external_id=Message.ExternalID(value=raw["id"]),
            reply_to_message_id=self._resolve_reply(raw, external_id_map),
            sequence_number=Message.SequenceNumber(value=sequence_number),
            date_unixtime=DateUnixtime(value=int(raw["date_unixtime"])),
            from_user=Message.UserName(value=raw["from"]),
            text=Message.Text(value=text),
            chat_id=chat_id,
        )

    @staticmethod
    def _resolve_reply(
            raw: dict,
            external_id_map: _ExternalIdMap
    ) -> Optional[ID]:
        reply_external_id = raw.get("reply_to_message_id")
        if reply_external_id is None:
            return None

        if raw.get("reply_to_peer_id"):
            return None

        return external_id_map.get(reply_external_id)

    @staticmethod
    def _extract_text(raw_text: str | list) -> str:
        if isinstance(raw_text, str):
            return raw_text.strip()

        return "".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in raw_text
        ).strip()

    def _persist(
            self,
            parsed_export: ParsedExport,
    ) -> None:
        self._uow.chat.create(parsed_export.chat)
        for message in parsed_export.messages:
            self._uow.message.create(message)
