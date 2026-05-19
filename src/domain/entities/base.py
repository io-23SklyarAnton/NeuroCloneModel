__all__ = [
    "Entity",
    "Aggregate",
]

import abc
import uuid
from typing import Any

import pydantic


class Entity(abc.ABC):
    @property
    @abc.abstractmethod
    def id(self) -> Any: ...


class Aggregate(Entity, abc.ABC):
    class IDomainEvent(pydantic.BaseModel, abc.ABC):
        class Payload(pydantic.BaseModel): ...

        id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
        object_id: str
        payload: Payload = pydantic.Field(default_factory=Payload)

    def __init__(self) -> None:
        self._events_to_publish: list[Aggregate.IDomainEvent] = []

    def publish_events(self) -> list[IDomainEvent]:
        events = self._events_to_publish
        self._events_to_publish = []
        return events
