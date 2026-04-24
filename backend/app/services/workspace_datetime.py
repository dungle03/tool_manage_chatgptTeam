from datetime import datetime, timezone

from app.services.workspace_schedule import normalize_schedule_datetime


def parse_datetime(value: str | int | float | datetime | None) -> datetime | None:
    if value is None:
        return None

    parsed: datetime | None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        epoch = float(value)
        if abs(epoch) >= 10_000_000_000:
            epoch /= 1000
        try:
            parsed = datetime.fromtimestamp(epoch, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    elif isinstance(value, str):
        if not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def coerce_utc(dt: datetime | None) -> datetime | None:
    return normalize_schedule_datetime(dt)
