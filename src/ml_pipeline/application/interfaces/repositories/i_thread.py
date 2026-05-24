__all__ = ["IThreadRepository"]

import abc
from typing import Optional

from common.domain.value_objects import ID
from common.infrastructure.i_base_repository import IBaseRepository
from ml_pipeline.domain.entities import ChatExport, Thread


class IThreadRepository(IBaseRepository[Thread]):
    @abc.abstractmethod
    async def get_by_id_optional(
            self,
            thread_id: ID,
    ) -> Optional[Thread]: ...

    @abc.abstractmethod
    async def get_all_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> list[Thread]: ...
