from abc import ABC, abstractmethod


class IVectorSearcher(ABC):
    @abstractmethod
    async def search(
            self,
            query: str,
            limit: int,
    ) -> list[str]:
        pass
