__all__ = [
    "NeuroCloneRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from common.domain.value_objects import ID, UserName
from common.exceptions.base import UnexpectedError
from common.infrastructure.db.base_sql_alchemy_repository import BaseRepository
from ml_pipeline.application.interfaces.repositories import INeuroCloneRepository
from ml_pipeline.domain.entities import ChatExport, NeuroClone as NeuroCloneAggregate
from ml_pipeline.infrastructure.db.models import NeuroClone as DBNeuroClone


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

    async def get_by_owner_id(
            self,
            owner_id: NeuroCloneAggregate.OwnerTelegramID,
    ) -> list[NeuroCloneAggregate]:
        query: Query = self.base_query()

        query = self._filter_by_owner_id(query, owner_id)

        db_neuroclones: list[DBNeuroClone] = query.all()
        return self.get_all(db_neuroclones)

    def from_aggregate_to_db_model(
            self,
            aggregate: NeuroCloneAggregate,
    ) -> DBNeuroClone:
        return DBNeuroClone(
            id=aggregate.id.value,
            owner_telegram_id=aggregate.owner_id.value,
            target_user_name=aggregate.target_user_name.value,
            source_chat_export_id=aggregate.source_chat_export_id.value,
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
            owner_id=NeuroCloneAggregate.OwnerTelegramID(value=db_model.owner_telegram_id),
            target_user_name=UserName(value=db_model.target_user_name),
            source_chat_export_id=ChatExport.ChatID(value=db_model.source_chat_export_id),
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

    def _filter_by_owner_id(
            self,
            query: Query,
            owner_id: NeuroCloneAggregate.OwnerTelegramID,
    ) -> Query:
        return query.filter(self.model.owner_telegram_id == owner_id.value)
