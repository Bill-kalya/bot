"""Single source of time. UTC only. No datetime.now() anywhere else."""
from __future__ import annotations

from datetime import UTC, datetime


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def to_iso(dt: datetime) -> str:
    """ISO8601 with microseconds, always UTC, always 'Z' suffix."""
    if dt.tzinfo is None:
        raise ValueError("naive datetime; use now_utc()")
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def from_iso(s: str) -> datetime:
    if not s.endswith("Z"):
        raise ValueError(f"expected UTC ISO8601 with Z: {s}")
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=UTC)