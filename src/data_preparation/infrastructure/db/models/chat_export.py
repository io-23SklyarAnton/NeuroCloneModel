__all__ = [
    "ChatExport",
]

from sqlalchemy import BigInteger, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from common.infrastructure.db.models.base import Base
from data_preparation.domain.entities import ChatExport as ChatExportAggregate


class ChatExport(Base):
    __tablename__ = "chat_exports"

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
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
    file_bucket: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    file_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    status: Mapped[ChatExportAggregate.Status] = mapped_column(
        Enum(ChatExportAggregate.Status, name="chat_export_status"),
        nullable=False,
    )
    n_messages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
