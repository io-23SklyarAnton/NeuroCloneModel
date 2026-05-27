__all__ = ["INeuroCloneRepository"]

import abc
from typing import Optional

from common.domain.value_objects import ID
from common.infrastructure.db.i_base_repository import IBaseRepository
from model_engine.domain.entities import NeuroClone


class INeuroCloneRepository(IBaseRepository[NeuroClone]):
    @abc.abstractmethod
    async def get_by_id_or_raise(
            self,
            neuroclone_id: ID,
    ) -> NeuroClone: ...

    @abc.abstractmethod
    async def get_by_id_optional(
            self,
            neuroclone_id: ID,
    ) -> Optional[NeuroClone]: ...
