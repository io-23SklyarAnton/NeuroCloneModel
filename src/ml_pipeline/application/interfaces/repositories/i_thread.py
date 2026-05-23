__all__ = ["IThreadRepository"]

import abc
from typing import Optional

from common.domain.value_objects import ID
from common.infrastructure.i_base_repository import IBaseRepository
from ml_pipeline.domain.entities import ChatExport, ParsedMessage, Thread


class IThreadRepository(IBaseRepository[Thread]):
    @abc.abstractmethod
    async def get_by_message_id(
            self,
            message_id: ID,
    ) -> Optional[Thread]: ...

    @abc.abstractmethod
    async def get_all_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> list[Thread]: ...

    @abc.abstractmethod
    async def get_messages_by_thread_id(
            self,
            thread_id: ID,
    ) -> list[ParsedMessage]: ...
