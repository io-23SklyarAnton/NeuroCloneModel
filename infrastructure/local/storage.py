from io import BytesIO
from pathlib import Path
from typing import Optional

from features.interfaces import IStorage


class LocalStorage(IStorage):
    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def save(
            self,
            bucket_name: str,
            file_object: BytesIO,
            file_name: str,
            extra_args: Optional[dict] = None,
    ) -> str:
        target_file = self._base_path / bucket_name / file_name
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_bytes(file_object.getvalue())
        return str(target_file)

    def load(
            self,
            bucket_name: str,
            file_name: str,
    ) -> str:
        return (self._base_path / bucket_name / file_name).read_text(encoding="utf-8")

    def exists(
            self,
            bucket_name: str,
            file_name: str,
    ) -> bool:
        return (self._base_path / bucket_name / file_name).exists()
