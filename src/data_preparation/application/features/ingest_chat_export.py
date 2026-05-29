__all__ = [
    "Command",
    "CommandHandler",
]

import asyncio
import json
from typing import Iterator, Optional

from common.application.base import ICommand
from common.application.interfaces import IStorage
from common.domain.value_objects import ID, UserName
from data_preparation.application.interfaces import IUnitOfWork
from data_preparation.domain.entities import ChatExport, ParsedMessage
from data_preparation.domain.value_objects import DateUnixtime

_ExternalIdMap = dict[int, ID]
_PERSIST_BATCH_SIZE = 1000


class Command(ICommand):
    chat_export_id: ChatExport.ChatID


class CommandHandler:
    _MEDIA_TYPE_TO_TYPE: dict[str, ParsedMessage.Type] = {
        "sticker": ParsedMessage.Type.STICKER,
        "video_file": ParsedMessage.Type.VIDEO_FILE,
        "voice_message": ParsedMessage.Type.VOICE_MESSAGE,
        "video_message": ParsedMessage.Type.VIDEO_MESSAGE,
        "animation": ParsedMessage.Type.ANIMATION,
        "audio_file": ParsedMessage.Type.AUDIO_FILE,
    }

    def __init__(
            self,
            uow: IUnitOfWork,
            storage: IStorage,
    ) -> None:
        self._uow = uow
        self._storage = storage

    async def handle(
            self,
            command: Command,
    ) -> None:
        chat_export: ChatExport = await self._uow.chat_export.get_by_id_or_raise(command.chat_export_id)

        if chat_export.status != ChatExport.Status.PENDING:
            print(
                f"ChatExport {chat_export.chat_id.value} is in {chat_export.status.value} state, "
                f"skipping ingest."
            )
            return

        raw_bytes = await self._storage.load(
            file_reference=chat_export.file_reference,
        )
        data = json.loads(raw_bytes)

        total_persisted = await self._persist_messages_in_batches(
            raw_messages=data["messages"],
            chat_export_id=chat_export.chat_id,
        )

        chat_export.record_message_count(total_persisted)
        chat_export.mark_ingested()
        self._uow.chat_export.update(chat_export)
        await self._uow.commit()

    async def _persist_messages_in_batches(
            self,
            raw_messages: list[dict],
            chat_export_id: ChatExport.ChatID,
    ) -> int:
        external_id_map: _ExternalIdMap = {}
        total_persisted = 0
        batch: list[ParsedMessage] = []

        for message in self._iter_parsed_messages(
                raw_messages=raw_messages,
                chat_export_id=chat_export_id,
                external_id_map=external_id_map,
        ):
            batch.append(message)

            if len(batch) >= _PERSIST_BATCH_SIZE:
                self._uow.parsed_message.create_many(batch)
                await self._uow.flush()
                total_persisted += len(batch)
                batch = []

        if batch:
            self._uow.parsed_message.create_many(batch)
            await self._uow.flush()
            total_persisted += len(batch)

        return total_persisted

    def _iter_parsed_messages(
            self,
            raw_messages: list[dict],
            chat_export_id: ChatExport.ChatID,
            external_id_map: _ExternalIdMap,
    ) -> Iterator[ParsedMessage]:
        sequence_number = 0

        for raw in raw_messages:
            message: Optional[ParsedMessage] = self._try_parse_message(
                raw=raw,
                sequence_number=sequence_number + 1,
                chat_export_id=chat_export_id,
                external_id_map=external_id_map,
            )
            if message is None:
                continue

            sequence_number += 1
            external_id_map[raw["id"]] = message.id
            yield message

    def _try_parse_message(
            self,
            raw: dict,
            sequence_number: int,
            chat_export_id: ChatExport.ChatID,
            external_id_map: _ExternalIdMap,
    ) -> Optional[ParsedMessage]:
        raw_type = raw.get("type")
        if raw_type == "message":
            from_user = raw.get("from")
            message_type = self._determine_content_type(raw)
        elif raw_type == "service":
            from_user = raw.get("actor")
            message_type = ParsedMessage.Type.SERVICE
        else:
            return None

        if not from_user:
            return None

        text = self._build_text(raw, message_type)
        if not text:
            return None

        return ParsedMessage.create(
            external_id=ParsedMessage.ExternalID(value=raw["id"]),
            reply_to_message_id=self._resolve_reply(raw, external_id_map),
            sequence_number=ParsedMessage.SequenceNumber(value=sequence_number),
            date_unixtime=DateUnixtime(value=int(raw["date_unixtime"])),
            from_user=UserName(value=from_user),
            text=ParsedMessage.Text(value=text),
            chat_export_id=chat_export_id,
            message_type=message_type,
        )

    def _determine_content_type(self, raw: dict) -> ParsedMessage.Type:
        if raw.get("photo"):
            return ParsedMessage.Type.IMAGE

        media_type = raw.get("media_type")
        if media_type:
            return self._MEDIA_TYPE_TO_TYPE.get(media_type, ParsedMessage.Type.OTHER_MEDIA)

        if raw.get("file"):
            return ParsedMessage.Type.FILE
        if raw.get("location_information"):
            return ParsedMessage.Type.LOCATION
        if raw.get("poll"):
            return ParsedMessage.Type.POLL

        return ParsedMessage.Type.TEXT

    @staticmethod
    def _resolve_reply(
            raw: dict,
            external_id_map: _ExternalIdMap,
    ) -> Optional[ID]:
        reply_external_id = raw.get("reply_to_message_id")
        if reply_external_id is None:
            return None

        if raw.get("reply_to_peer_id"):
            return None

        return external_id_map.get(reply_external_id)

    def _build_text(
            self,
            raw: dict,
            content_type: ParsedMessage.Type,
    ) -> str:
        if content_type == ParsedMessage.Type.SERVICE:
            return self._build_service_text(raw)

        caption: str = self._extract_text(raw.get("text", ""))
        prefix: Optional[str] = self._build_prefix(raw, content_type)

        if prefix and caption:
            return f"{prefix} {caption}"
        if prefix:
            return prefix

        return caption

    @staticmethod
    def _build_service_text(raw: dict) -> str:
        action = raw.get("action")
        if not action:
            return ""

        return f"[SERVICE {action}]"

    def _build_prefix(
            self,
            raw: dict,
            content_type: ParsedMessage.Type,
    ) -> Optional[str]:
        if content_type == ParsedMessage.Type.TEXT:
            return None

        if content_type == ParsedMessage.Type.STICKER:
            emoji = raw.get("sticker_emoji")
            return f"[STICKER {emoji}]" if emoji else "[STICKER]"

        if content_type == ParsedMessage.Type.OTHER_MEDIA:
            media_type = raw.get("media_type", "media")
            return f"[{media_type.upper()}]"

        return f"[{content_type.value}]"

    @staticmethod
    def _extract_text(raw_text: str | list) -> str:
        if isinstance(raw_text, str):
            return raw_text.strip()

        return "".join(
            part if isinstance(part, str) else part.get("text", "")
            for part in raw_text
        ).strip()


if __name__ == "__main__":
    from pathlib import Path

    from data_preparation.infrastructure.in_memory.uow import InMemoryUnitOfWork
    from data_preparation.infrastructure.local import LocalStorage

    _BASE_DIR = Path(__file__).parent.parent.parent.parent
    uow = InMemoryUnitOfWork()
    storage = LocalStorage(
        base_path=_BASE_DIR / "eval" / "data",
    )

    ingest_handler = CommandHandler(
        uow=uow,
        storage=storage,
    )
    command = Command(chat_export_id=ChatExport.ChatID(value=1))
    asyncio.run(ingest_handler.handle(command))
