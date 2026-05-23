__all__ = ["IChatExportRepository"]

import abc
from typing import Optional

from common.infrastructure.i_base_repository import IBaseRepository
from ml_pipeline.domain.entities import ChatExport, ParsedMessage


class IChatExportRepository(IBaseRepository[ChatExport]):
    @abc.abstractmethod
    async def get_by_id_or_raise(
            self,
            chat_id: ChatExport.ChatID,
    ) -> ChatExport: ...

    @abc.abstractmethod
    async def get_by_id_optional(
            self,
            chat_id: ChatExport.ChatID,
    ) -> Optional[ChatExport]: ...

    @abc.abstractmethod
    async def get_messages_batch(
            self,
            chat_id: ChatExport.ChatID,
            offset: int,
            limit: int,
    ) -> list[ParsedMessage]: ...
