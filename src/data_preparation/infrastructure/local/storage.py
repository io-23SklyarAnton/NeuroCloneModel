__all__ = ["LocalStorage"]

import asyncio
from io import BytesIO
from pathlib import Path

from common.domain.value_objects import FileReference
from data_preparation.application.interfaces import IStorage


class LocalStorage(IStorage):
    def __init__(
            self,
            base_path: Path,
    ) -> None:
        self._base_path = base_path

    async def save(
            self,
            file_object: BytesIO,
            file_reference: FileReference,
    ) -> str:
        target_file: Path = self._resolve_path(file_reference)

        def _write_file() -> None:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(file_object.getvalue())

        await asyncio.to_thread(_write_file)
        return str(target_file)

    async def load(
            self,
            file_reference: FileReference,
    ) -> bytes:
        target_file: Path = self._resolve_path(file_reference)
        return await asyncio.to_thread(target_file.read_bytes)

    async def exists(
            self,
            file_reference: FileReference,
    ) -> bool:
        target_file: Path = self._resolve_path(file_reference)
        return await asyncio.to_thread(target_file.exists)

    def _resolve_path(
            self,
            file_reference: FileReference,
    ) -> Path:
        return self._base_path / file_reference.bucket / file_reference.key
