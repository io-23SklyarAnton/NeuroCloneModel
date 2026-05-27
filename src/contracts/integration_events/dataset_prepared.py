__all__ = [
    "DatasetPreparedEvent",
]

import datetime
import uuid

import pydantic


class DatasetPreparedEvent(pydantic.BaseModel):
    event_id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)
    occurred_at: datetime.datetime = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )
    dataset_id: uuid.UUID
    owner_telegram_id: int
    target_user_name: str
    dataset_file_key: str
    source_chat_export_id: int
    n_pairs: int
