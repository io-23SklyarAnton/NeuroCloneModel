__all__ = ["IStorage"]

import abc
from io import BytesIO
from pathlib import Path

from common.domain.value_objects import FileReference


class IStorage(abc.ABC):
    @abc.abstractmethod
    async def save(
            self,
            file_object: BytesIO,
            file_reference: FileReference,
    ) -> str: ...

    @abc.abstractmethod
    async def load(
            self,
            file_reference: FileReference,
    ) -> bytes: ...

    @abc.abstractmethod
    async def exists(
            self,
            file_reference: FileReference,
    ) -> bool: ...

    @abc.abstractmethod
    def resolve_local_path(
            self,
            file_reference: FileReference,
    ) -> Path: ...
