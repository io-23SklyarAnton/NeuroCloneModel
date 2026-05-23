__all__ = ["IBaseRepository"]

import abc
from typing import Generic, TypeVar

from common.domain.entities import Aggregate

T_Agg = TypeVar("T_Agg", bound=Aggregate)


class IBaseRepository(abc.ABC, Generic[T_Agg]):
    @abc.abstractmethod
    def create(self, aggregate: T_Agg) -> None: ...

    @abc.abstractmethod
    def update(self, aggregate: T_Agg) -> None: ...
