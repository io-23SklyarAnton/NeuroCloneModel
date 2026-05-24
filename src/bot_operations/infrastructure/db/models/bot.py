__all__ = [
    "Bot",
]

import uuid

from sqlalchemy import BigInteger, Enum, String, UniqueConstraint
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
    status: Mapped[BotAggregate.BotStatus] = mapped_column(
        Enum(BotAggregate.BotStatus, name="bot_status"),
        nullable=False,
    )
    linked_dataset_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        default=list,
    )

    __table_args__ = (
        UniqueConstraint("token", name="unique_bot_token"),
    )
