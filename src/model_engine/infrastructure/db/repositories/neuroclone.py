__all__ = [
    "NeuroCloneRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from common.domain.value_objects import ID, UserName, OwnerTelegramID
from common.exceptions.base import UnexpectedError
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository
from model_engine.application.interfaces.repositories import INeuroCloneRepository
from model_engine.domain.entities import NeuroClone as NeuroCloneAggregate
from model_engine.infrastructure.db.models import NeuroClone as DBNeuroClone


class NeuroCloneRepository(
    INeuroCloneRepository,
    BaseRepository[NeuroCloneAggregate, DBNeuroClone],
):
    @property
    def model(self) -> type[DBNeuroClone]:
        return DBNeuroClone

    async def get_by_id_or_raise(
            self,
            neuroclone_id: ID,
    ) -> NeuroCloneAggregate:
        neuroclone: Optional[NeuroCloneAggregate] = await self.get_by_id_optional(neuroclone_id)
        if neuroclone is None:
            raise UnexpectedError(f"NeuroClone with id={neuroclone_id.value} not found")

        return neuroclone

    async def get_by_id_optional(
            self,
            neuroclone_id: ID,
    ) -> Optional[NeuroCloneAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_id(query, neuroclone_id)

        db_neuroclone: Optional[DBNeuroClone] = query.first()
        return self.get_optional(db_neuroclone)

    def from_aggregate_to_db_model(
            self,
            aggregate: NeuroCloneAggregate,
    ) -> DBNeuroClone:
        return DBNeuroClone(
            id=aggregate.id.value,
            owner_telegram_id=aggregate.owner_id.value,
            target_user_name=aggregate.target_user_name.value,
            dataset_file_key=aggregate.dataset_file_key.value,
            status=aggregate.status,
            adapter_path=(
                aggregate.adapter_path.value
                if aggregate.adapter_path is not None else None
            ),
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBNeuroClone,
    ) -> NeuroCloneAggregate:
        return NeuroCloneAggregate(
            id_=ID(value=db_model.id),
            owner_id=OwnerTelegramID(value=db_model.owner_telegram_id),
            target_user_name=UserName(value=db_model.target_user_name),
            dataset_file_key=NeuroCloneAggregate.DatasetFileKey(value=db_model.dataset_file_key),
            status=db_model.status,
            adapter_path=(
                NeuroCloneAggregate.AdapterPath(value=db_model.adapter_path)
                if db_model.adapter_path is not None else None
            ),
        )

    def _filter_by_id(
            self,
            query: Query,
            neuroclone_id: ID,
    ) -> Query:
        return query.filter(self.model.id == neuroclone_id.value)
