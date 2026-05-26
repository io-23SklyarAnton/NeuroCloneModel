__all__ = [
    "NeuroCloneSnapshot",
    "NeuroCloneReader",
]

import uuid
from typing import Optional, Protocol

import pydantic


class NeuroCloneSnapshot(pydantic.BaseModel):
    neuroclone_id: uuid.UUID
    is_ready: bool
    target_user_name: str
    adapter_path: Optional[str]


class NeuroCloneReader(Protocol):
    async def get_snapshot(
            self,
            neuroclone_id: uuid.UUID,
    ) -> Optional[NeuroCloneSnapshot]: ...

    async def is_ready(
            self,
            neuroclone_id: uuid.UUID,
    ) -> bool: ...
