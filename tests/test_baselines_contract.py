from datetime import UTC, datetime

from core.types import Candle
from research import baselines


def _candles(n=60, base=60_000.0, step=10.0):
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    out = []
    for i in range(n):
        p = base + i * step
        out.append(Candle(
            ts=t0, open=p, high=p + 5, low=p - 5, close=p, volume=1.0,
        ))
    return out


def test_all_baselines_emit_full_signal_contract():
    for fn in (baselines.buy_and_hold_predict, baselines.random_predict):
        sig = fn(_candles(), "BTC/USDT:USDT", "test")
        assert sig.direction in (-1, 0, 1)
        assert 0.0 <= sig.confidence <= 1.0
        assert sig.horizon_minutes > 0
        assert sig.source_version == "test"


def test_random_is_deterministic_given_close():
    c = _candles()
    a = baselines.random_predict(c, "BTC/USDT:USDT", "test")
    b = baselines.random_predict(c, "BTC/USDT:USDT", "test")
    assert a.direction == b.direction