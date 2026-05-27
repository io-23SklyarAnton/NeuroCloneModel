__all__ = [
    "NeuroCloneReadyEvent",
]

import datetime
import uuid

import pydantic


class NeuroCloneReadyEvent(pydantic.BaseModel):
    event_id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    occurred_at: datetime.datetime = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )
    neuroclone_id: uuid.UUID
    owner_telegram_id: int
    target_user_name: str
