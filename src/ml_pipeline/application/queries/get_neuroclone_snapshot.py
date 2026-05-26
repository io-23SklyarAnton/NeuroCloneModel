__all__ = [
    "NeuroCloneSnapshot",
    "NeuroCloneReader",
]

import uuid
from typing import Optional

import pydantic

from common.domain.value_objects import ID
from ml_pipeline.application.interfaces import IUnitOfWork
from ml_pipeline.domain.entities import NeuroClone


class NeuroCloneSnapshot(pydantic.BaseModel):
    neuroclone_id: uuid.UUID
    is_ready: bool
    target_user_name: str
    adapter_path: Optional[str]


class NeuroCloneReader:
    def __init__(
            self,
            uow: IUnitOfWork,
    ) -> None:
        self._uow = uow

    async def get_snapshot(
            self,
            neuroclone_id: uuid.UUID,
    ) -> Optional[NeuroCloneSnapshot]:
        neuroclone: Optional[NeuroClone] = await self._uow.neuroclone.get_by_id_optional(
            ID(value=neuroclone_id),
        )
        if neuroclone is None:
            return None

        return NeuroCloneSnapshot(
            neuroclone_id=neuroclone.id.value,
            is_ready=neuroclone.is_ready,
            target_user_name=neuroclone.target_user_name.value,
            adapter_path=(
                neuroclone.adapter_path.value
                if neuroclone.adapter_path is not None else None
            ),
        )

    async def is_ready(
            self,
            neuroclone_id: uuid.UUID,
    ) -> bool:
        neuroclone: Optional[NeuroClone] = await self._uow.neuroclone.get_by_id_optional(
            neuroclone_id=ID(value=neuroclone_id),
        )
        return neuroclone is not None and neuroclone.is_ready
