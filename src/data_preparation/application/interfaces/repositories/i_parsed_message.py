__all__ = ["IParsedMessageRepository"]

import abc
from typing import Optional

from common.domain.value_objects import ID, UserName
from common.infrastructure.db.i_base_repository import IBaseRepository
from data_preparation.domain.entities import ChatExport, ParsedMessage


class IParsedMessageRepository(IBaseRepository[ParsedMessage]):
    @abc.abstractmethod
    def create_many(
            self,
            messages: list[ParsedMessage],
    ) -> None: ...

    @abc.abstractmethod
    async def get_by_id_optional(
            self,
            message_id: ID,
    ) -> Optional[ParsedMessage]: ...

    @abc.abstractmethod
    async def get_batch_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
            offset: int,
            limit: int,
    ) -> list[ParsedMessage]: ...

    @abc.abstractmethod
    async def get_target_user_sequence_numbers_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
            target_user_name: UserName,
    ) -> list[int]: ...

    @abc.abstractmethod
    async def get_by_thread_id(
            self,
            thread_id: ID,
    ) -> list[ParsedMessage]: ...

    @abc.abstractmethod
    async def get_by_chat_and_external_id_optional(
            self,
            chat_export_id: ChatExport.ChatID,
            external_id: ParsedMessage.ExternalID,
    ) -> Optional[ParsedMessage]: ...

    @abc.abstractmethod
    async def count_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> int: ...
