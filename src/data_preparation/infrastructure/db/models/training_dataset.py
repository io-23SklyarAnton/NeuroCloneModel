__all__ = [
    "TrainingDataset",
]

import datetime
import uuid

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db.models.base import Base


class TrainingDataset(Base):
    __tablename__ = "training_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    owner_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    target_user: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    source_chat_export_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    file_bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    file_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    n_pairs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    built_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
    )
