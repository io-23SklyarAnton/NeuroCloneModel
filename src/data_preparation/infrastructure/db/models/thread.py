__all__ = [
    "Thread",
]

import uuid

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db.models.base import Base


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    chat_export_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_exports.chat_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
