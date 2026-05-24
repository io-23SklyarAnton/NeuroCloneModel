__all__ = [
    "LiveMessage",
]

import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from bot_operations.infrastructure.db.models.live_chat import LiveChat


class LiveMessage(Base):
    __tablename__ = "live_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    live_chat_external_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("live_chats.external_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_user: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    text: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    sent_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
    )

    live_chat: Mapped["LiveChat"] = relationship(
        "LiveChat",
        back_populates="recent_messages",
    )
