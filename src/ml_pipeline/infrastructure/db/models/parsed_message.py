__all__ = [
    "ParsedMessage",
]

import uuid
from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db.models.base import Base
from ml_pipeline.domain.entities import ParsedMessage as ParsedMessageAggregate


class ParsedMessage(Base):
    __tablename__ = "parsed_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )
    external_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    reply_to_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    date_unixtime: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    from_user: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    text: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    chat_export_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_exports.chat_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("threads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    message_type: Mapped[ParsedMessageAggregate.Type] = mapped_column(
        Enum(ParsedMessageAggregate.Type, name="parsed_message_type"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "chat_export_id",
            "external_id",
            name="unique_parsed_message_chat_export_external",
        ),
    )
