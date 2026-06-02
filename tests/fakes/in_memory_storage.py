from io import BytesIO
from pathlib import Path
from common.application.interfaces import IStorage
from common.domain.value_objects import FileReference


class InMemoryStorage(IStorage):

    def __init__(self) -> None:
        self._files: dict[FileReference, bytes] = {}

    async def save(self, file_object: BytesIO, file_reference: FileReference) -> str:
        file_object.seek(0)
        self._files[file_reference] = file_object.read()
        file_object.seek(0)
        return str(self.resolve_local_path(file_reference))

    async def load(self, file_reference: FileReference) -> bytes:
        if file_reference not in self._files:
            raise FileNotFoundError(file_reference.full_path)
        return self._files[file_reference]

    async def exists(self, file_reference: FileReference) -> bool:
        return file_reference in self._files

    def resolve_local_path(self, file_reference: FileReference) -> Path:
        return Path('/tmp/fakes') / file_reference.bucket / file_reference.key

    def put(self, file_reference: FileReference, content: bytes) -> None:
        self._files[file_reference] = content

    def stored_count(self) -> int:
        return len(self._files)
