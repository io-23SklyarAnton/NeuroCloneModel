from datetime import datetime, timezone


def get_now_datetime() -> datetime:
    return datetime.now(tz=timezone.utc)
