import abc
from io import BytesIO
from typing import Optional


class IStorage(abc.ABC):
    @abc.abstractmethod
    def save(
            self,
            bucket_name: str,
            file_object: BytesIO,
            file_name: str,
            extra_args: Optional[dict] = None,
    ) -> str: ...

    @abc.abstractmethod
    def load(
            self,
            bucket_name: str,
            file_name: str,
    ) -> str: ...

    @abc.abstractmethod
    def exists(
            self,
            bucket_name: str,
            file_name: str,
    ) -> bool: ...
