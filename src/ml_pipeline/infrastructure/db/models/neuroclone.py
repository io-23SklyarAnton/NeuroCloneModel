__all__ = [
    "NeuroClone",
]

import uuid
from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db.models.base import Base
from ml_pipeline.domain.entities import NeuroClone as NeuroCloneAggregate


class NeuroClone(Base):
    __tablename__ = "neuroclones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    owner_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    target_user_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    source_chat_export_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_exports.chat_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[NeuroCloneAggregate.Status] = mapped_column(
        Enum(NeuroCloneAggregate.Status, name="neuroclone_status"),
        nullable=False,
    )
    adapter_path: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
