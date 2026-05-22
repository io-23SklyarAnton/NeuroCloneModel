import abc
from io import BytesIO
from typing import Optional


class IStorage(abc.ABC):
    @abc.abstractmethod
    async def save(
            self,
            file_object: BytesIO,
            file_name: str,
            extra_args: Optional[dict] = None,
    ) -> str: ...

    @abc.abstractmethod
    async def load(
            self,
            file_name: str,
    ) -> bytes: ...

    @abc.abstractmethod
    async def exists(
            self,
            file_name: str,
    ) -> bool: ...
