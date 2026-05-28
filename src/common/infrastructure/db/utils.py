__all__ = [
    "get_session_maker",
    "get_db",
    "get_utc_now_naive",
    "current_unix_timestamp",
]

import datetime
import time

from sqlalchemy.orm import Session, sessionmaker

from common.infrastructure.db.config import db_settings


def get_session_maker() -> sessionmaker:
    return sessionmaker(
        autoflush=False,
        autocommit=False,
        bind=db_settings.engine,
    )


def get_db() -> Session:
    return get_session_maker()()


def get_utc_now_naive() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


def current_unix_timestamp() -> int:
    return int(time.time())
