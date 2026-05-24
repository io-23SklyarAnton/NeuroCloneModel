from common.infrastructure.db.models.base import Base as Base
from common.infrastructure.db.models.outbox_message import OutboxMessage

__all__ = [
    "Base",
    "OutboxMessage",
]
