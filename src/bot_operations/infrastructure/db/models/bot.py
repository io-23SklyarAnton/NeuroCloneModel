__all__ = [
    "Bot",
]

import uuid
from typing import Optional

from sqlalchemy import BigInteger, Enum, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
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
    target_user_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    status: Mapped[BotAggregate.BotStatus] = mapped_column(
        Enum(BotAggregate.BotStatus, name="bot_status"),
        nullable=False,
    )
    linked_dataset_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
    )
    lora_path: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
        default=None,
    )
    reply_period: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("token", name="unique_bot_token"),
    )
