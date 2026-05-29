__all__ = [
    "NeuroClone",
]

import uuid
from typing import Optional

from sqlalchemy import BigInteger, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db.models.base import Base
from model_engine.domain.entities import NeuroClone as NeuroCloneAggregate


class NeuroClone(Base):
    __tablename__ = "neuroclones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    owner_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    target_user_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    dataset_file_bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    dataset_file_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    status: Mapped[NeuroCloneAggregate.Status] = mapped_column(
        Enum(NeuroCloneAggregate.Status, name="neuroclone_status"),
        nullable=False,
    )
    adapter_file_bucket: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    adapter_file_key: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    reply_period: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
