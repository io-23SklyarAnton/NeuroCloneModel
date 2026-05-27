__all__ = ["LocalStorage"]

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional

from data_preparation.application.interfaces import IStorage


class LocalStorage(IStorage):
    def __init__(
            self,
            base_path: Path,
            bucket_name: str,
    ) -> None:
        self._base_path = base_path
        self._bucket_name = bucket_name

    async def save(
            self,
            file_object: BytesIO,
            file_name: str,
            extra_args: Optional[dict] = None,
    ) -> str:
        target_file = self._base_path / self._bucket_name / file_name

        def _write_file() -> None:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_bytes(file_object.getvalue())

        await asyncio.to_thread(_write_file)
        return str(target_file)

    async def load(
            self,
            file_name: str,
    ) -> bytes:
        target_file = self._base_path / self._bucket_name / file_name
        return await asyncio.to_thread(target_file.read_bytes)

    async def exists(
            self,
            file_name: str,
    ) -> bool:
        target_file = self._base_path / self._bucket_name / file_name
        return await asyncio.to_thread(target_file.exists)
