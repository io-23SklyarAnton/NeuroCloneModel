__all__ = [
    "LiveChat",
]

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.infrastructure.db.models.base import Base

if TYPE_CHECKING:
    from bot_operations.infrastructure.db.models.live_message import LiveMessage


class LiveChat(Base):
    __tablename__ = "live_chats"

    external_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    recent_messages: Mapped[list["LiveMessage"]] = relationship(
        "LiveMessage",
        back_populates="live_chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LiveMessage.sent_at",
    )
