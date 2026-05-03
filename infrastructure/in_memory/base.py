from typing import Generic, Optional, TypeVar, Any

from domain.entities.base import Aggregate
from features.interfaces.repositories import IBaseRepository

T_Aggregate = TypeVar("T_Aggregate", bound=Aggregate)


class InMemoryBaseRepository(IBaseRepository[T_Aggregate], Generic[T_Aggregate]):
    def __init__(
            self,
            storage: dict[Any, T_Aggregate]
    ):
        self._storage = storage

    def create(
            self,
            aggregate: T_Aggregate,
    ) -> None:
        self._storage[aggregate.id] = aggregate

    def update(
            self,
            aggregate: T_Aggregate,
    ) -> None:
        if aggregate.id not in self._storage:
            raise ValueError(f"Entity with id {aggregate.id} not found for update")

        self._storage[aggregate.id] = aggregate

    def get_optional(
            self,
            id_: Any,
    ) -> Optional[T_Aggregate]:
        return self._storage.get(id_)

    def get_or_raise(
            self,
            id_: Any,
    ) -> T_Aggregate:
        aggregate: Optional[T_Aggregate] = self._storage.get(id_)

        if not aggregate:
            raise ValueError(f"Entity with id {id_} not found")

        return aggregate

    def get_all(self) -> list[T_Aggregate]:
        return list(self._storage.values())
