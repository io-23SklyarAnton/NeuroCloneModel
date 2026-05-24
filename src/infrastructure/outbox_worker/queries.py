__all__ = [
    "get_unscheduled_outbox_messages",
]

from sqlalchemy.orm import Session

from common.infrastructure.db.models import OutboxMessage


def get_unscheduled_outbox_messages(session: Session) -> list[OutboxMessage]:
    return session.query(OutboxMessage).filter(OutboxMessage.scheduled_at.is_(None)).all()  # type: ignore[return-value]
