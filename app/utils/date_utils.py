from datetime import UTC, datetime

def ensure_utc(dt: datetime) -> datetime:
    """Garante que o datetime seja timezone-aware (UTC)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def utc_now() -> datetime:
    """Retorna datetime atual em UTC timezone-aware"""
    return datetime.now(UTC)
