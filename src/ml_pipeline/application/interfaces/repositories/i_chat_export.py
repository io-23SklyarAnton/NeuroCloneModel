__all__ = ["IChatExportRepository"]

import abc
from typing import Optional

from common.infrastructure.db.i_base_repository import IBaseRepository
from ml_pipeline.domain.entities import ChatExport


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
