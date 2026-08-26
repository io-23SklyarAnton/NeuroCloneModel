from abc import ABC, abstractmethod

from common.domain.value_objects import DocumentChunk


class IVectorIndexer(ABC):
    @abstractmethod
    async def upsert(
            self,
            chunks: list[DocumentChunk],
    ) -> None:
        pass