__all__ = [
    "NeuroCloneRepository",
]

from typing import Optional

from sqlalchemy.orm import Query

from common.domain.value_objects import (
    FileReference,
    ID,
    OwnerTelegramID,
    ReplyPeriod,
    UserName,
)
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
        adapter_file_reference: Optional[FileReference] = aggregate.adapter_file_reference
        return DBNeuroClone(
            id=aggregate.id.value,
            owner_telegram_id=aggregate.owner_id.value,
            target_user_name=aggregate.target_user_name.value,
            dataset_file_bucket=aggregate.dataset_file_reference.bucket,
            dataset_file_key=aggregate.dataset_file_reference.key,
            status=aggregate.status,
            adapter_file_bucket=(
                adapter_file_reference.bucket
                if adapter_file_reference is not None else None
            ),
            adapter_file_key=(
                adapter_file_reference.key
                if adapter_file_reference is not None else None
            ),
            reply_period=aggregate.reply_period.value,
        )

    def from_db_model_to_aggregate(
            self,
            db_model: DBNeuroClone,
    ) -> NeuroCloneAggregate:
        return NeuroCloneAggregate(
            id_=ID(value=db_model.id),
            owner_id=OwnerTelegramID(value=db_model.owner_telegram_id),
            target_user_name=UserName(value=db_model.target_user_name),
            dataset_file_reference=FileReference(
                bucket=db_model.dataset_file_bucket,
                key=db_model.dataset_file_key,
            ),
            status=db_model.status,
            adapter_file_reference=(
                FileReference(
                    bucket=db_model.adapter_file_bucket,
                    key=db_model.adapter_file_key,
                )
                if db_model.adapter_file_bucket is not None
                and db_model.adapter_file_key is not None
                else None
            ),
            reply_period=ReplyPeriod(value=db_model.reply_period),
        )

    def _filter_by_id(
            self,
            query: Query,
            neuroclone_id: ID,
    ) -> Query:
        return query.filter(self.model.id == neuroclone_id.value)
