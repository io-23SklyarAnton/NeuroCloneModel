__all__ = [
    "Bot",
]

import uuid
from typing import Optional

from sqlalchemy import BigInteger, Enum, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from bot_operations.domain.entities import Bot as BotAggregate
from common.infrastructure.db.models.base import Base


class Bot(Base):
    __tablename__ = "bots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    owner_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    neuroclone_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    status: Mapped[BotAggregate.BotStatus] = mapped_column(
        Enum(BotAggregate.BotStatus, name="bot_status"),
        nullable=False,
    )
    reply_period: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("token", name="unique_bot_token"),
    )
