__all__ = [
    "OutboxMessage",
]

import datetime
import uuid
from typing import Optional

from sqlalchemy import DateTime, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db.models.base import Base
from common.infrastructure.db.utils import get_utc_now_naive


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    object_id: Mapped[str] = mapped_column(nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=get_utc_now_naive,
    )
    scheduled_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
        default=None,
    )
