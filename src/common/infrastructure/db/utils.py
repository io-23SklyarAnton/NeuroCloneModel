__all__ = [
    "get_session_maker",
    "get_db",
    "get_utc_now_naive",
    "current_unix_timestamp",
    "init_db",
]

import datetime
import importlib
import time

from sqlalchemy.orm import Session, sessionmaker

from common.infrastructure.db.config import db_settings
from common.infrastructure.db.models import Base


_MODEL_PACKAGES: tuple[str, ...] = (
    "common.infrastructure.db.models",
    "bot_operations.infrastructure.db.models",
    "data_preparation.infrastructure.db.models",
    "iam.infrastructure.db.models",
    "model_engine.infrastructure.db.models",
)


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


def init_db() -> None:
    for package_name in _MODEL_PACKAGES:
        importlib.import_module(package_name)

    Base.metadata.create_all(bind=db_settings.engine)
