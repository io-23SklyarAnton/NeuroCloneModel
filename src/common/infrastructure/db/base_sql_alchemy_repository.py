import abc
from typing import Generic, Optional, TypeVar

from sqlalchemy.orm import Query, Session

from common.domain.entities import Aggregate
from common.exceptions.base import UnexpectedError

from common.infrastructure.db.i_base_repository import IBaseRepository
from common.infrastructure.db.models import Base, OutboxMessage

T_Aggregate = TypeVar("T_Aggregate", bound=Aggregate)
T_DB_Model = TypeVar("T_DB_Model", bound=Base)


class BaseRepository(IBaseRepository[T_Aggregate], Generic[T_Aggregate, T_DB_Model]):
    def __init__(self, session: Session):
        self._session = session

    def create(self, aggregate: T_Aggregate) -> None:
        self._session.add(self.from_aggregate_to_db_model(aggregate))
        self._publish_events(aggregate)

    def update(self, aggregate: T_Aggregate) -> None:
        self._session.merge(self.from_aggregate_to_db_model(aggregate))
        self._publish_events(aggregate)

    def base_query(self) -> Query:
        return self._session.query(self.model)

    def get_optional(self, db_model: Optional[T_DB_Model]) -> Optional[T_Aggregate]:
        if not db_model:
            return None

        return self.from_db_model_to_aggregate(db_model)

    def get_or_raise(self, db_model: Optional[T_DB_Model]) -> T_Aggregate:
        if not db_model:
            raise UnexpectedError(f"entity not found {self.model.__name__}")

        return self.from_db_model_to_aggregate(db_model)

    def get_all(self, db_models: list[T_DB_Model]) -> list[T_Aggregate]:
        return [self.from_db_model_to_aggregate(db_model) for db_model in db_models]

    @property
    @abc.abstractmethod
    def model(self) -> type[T_DB_Model]:
        ...

    @abc.abstractmethod
    def from_aggregate_to_db_model(self, aggregate: T_Aggregate) -> T_DB_Model:
        ...

    @abc.abstractmethod
    def from_db_model_to_aggregate(self, db_model: T_DB_Model) -> T_Aggregate:
        ...

    def _publish_events(self, aggregate: T_Aggregate) -> None:
        for event in aggregate.publish_events():
            self._session.add(OutboxMessage(
                id=event.id,
                object_id=event.object_id,
                name=event.__class__.__name__,
                data=event.payload.model_dump(mode="json"),
            ))
