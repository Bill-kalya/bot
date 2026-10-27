from datetime import UTC, datetime, timedelta

from core.types import Candle
from data.features import (
    _atr_14,
    _classify_regime,
    _trend_strength,
    _volatility_percentile,
)


def _candles(n, base=60_000.0, step=0.0, noise=0.0):
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    out = []
    for i in range(n):
        p = base + i * step
        out.append(Candle(
            ts=t0 + timedelta(minutes=i),
            open=p - noise / 2, high=p + noise / 2,
            low=p - noise / 2, close=p, volume=1.0,
        ))
    return out


def test_atr_14_flat_market_is_zero():
    c = _candles(30, step=0.0, noise=0.0)
    assert _atr_14(c) == 0.0


def test_atr_14_volatile_market_is_positive():
    c = _candles(30, noise=100.0)
    assert _atr_14(c) > 0.0


def test_volatility_percentile_in_range():
    c = _candles(120, noise=50.0)
    pct = _volatility_percentile(c, 60)
    assert 0.0 <= pct <= 1.0


def test_trend_strength_zero_on_flat():
    c = _candles(120, step=0.0)
    assert _trend_strength(c, 60) < 1e-9


def test_trend_strength_positive_on_uptrend():
    c = _candles(120, base=60_000, step=10.0)
    assert _trend_strength(c, 60) > 0.0


def test_classify_regime_all_four():
    assert _classify_regime(0.8, 0.01) == "high_vol_trend"
    assert _classify_regime(0.8, 0.001) == "high_vol_chop"
    assert _classify_regime(0.3, 0.01) == "low_vol_trend"
    assert _classify_regime(0.3, 0.001) == "low_vol_chop"