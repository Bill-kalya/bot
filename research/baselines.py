"""Reference strategies for comparison.

Each returns a Signal, same contract as any real strategy. The simulator
runs them through the identical risk engine and cost model. This is the
only honest way to answer "does the strategy beat simple alternatives?".
"""
from __future__ import annotations

from core.clock import now_utc
from core.types import Signal

HORIZON = 15


def buy_and_hold_predict(candles: list, symbol: str, version: str) -> Signal:
    """Always long, every minute, until the end of the backtest window.

    In a simulator that opens one position at a time, this is effectively
    'long whenever flat'. The comparison is against the same risk engine.
    """
    return Signal(
        decision_time=now_utc(), symbol=symbol, horizon_minutes=HORIZON,
        direction=1, confidence=0.9,
        expected_signed_return=0.005,
        expected_volatility=_vol(candles),
        source_version=version,
    )


def random_predict(candles: list, symbol: str, version: str) -> Signal:
    """Deterministic pseudo-random, seeded by the last candle's close.

    Deterministic so backtests are reproducible. Not for live use.
    """
    import hashlib
    seed_bytes = hashlib.sha256(f"{candles[-1].close}".encode()).digest()
    coin = seed_bytes[0] / 255.0  # [0, 1)
    direction = 1 if coin < 0.5 else -1
    return Signal(
        decision_time=now_utc(), symbol=symbol, horizon_minutes=HORIZON,
        direction=direction, confidence=0.5,
        expected_signed_return=0.005 * direction,
        expected_volatility=_vol(candles),
        source_version=version,
    )


def _vol(candles: list) -> float:
    import statistics
    if len(candles) < 3:
        return 0.005
    closes = [c.close for c in candles[-30:]]
    rets = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    return statistics.pstdev(rets) if len(rets) > 1 else 0.005