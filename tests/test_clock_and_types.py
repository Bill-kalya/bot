from datetime import UTC

from core.clock import from_iso, now_utc, to_iso


def test_now_is_utc_aware() -> None:
    assert now_utc().tzinfo is UTC


def test_roundtrip_iso() -> None:
    t = now_utc()
    assert from_iso(to_iso(t)) == t


def test_naive_datetime_rejected() -> None:
    from datetime import datetime

    import pytest
    with pytest.raises(ValueError):
        to_iso(datetime(2026, 1, 1))  # noqa: DTZ001 (intentional naive dt for test)