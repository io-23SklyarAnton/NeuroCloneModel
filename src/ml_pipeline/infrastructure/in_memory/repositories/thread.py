__all__ = ["InMemoryThreadRepository"]

from typing import Optional

from common.domain.value_objects import ID
from common.infrastructure.in_memory_repository import InMemoryBaseRepository
from ml_pipeline.application.interfaces.repositories import IThreadRepository
from ml_pipeline.domain.entities import ChatExport, Thread


class InMemoryThreadRepository(InMemoryBaseRepository[Thread], IThreadRepository):
    def __init__(
            self,
            storage: dict[ID, Thread],
    ):
        super().__init__(storage)

    async def get_by_id_optional(
            self,
            thread_id: ID,
    ) -> Optional[Thread]:
        return self.get_optional(thread_id)

    async def get_all_by_chat_export_id(
            self,
            chat_export_id: ChatExport.ChatID,
    ) -> list[Thread]:
        return [
            thread for thread in self._storage.values()
            if thread.chat_export_id == chat_export_id
        ]
