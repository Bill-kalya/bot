"""Momentum baseline. Not the final AI — exists so the whole system can be
tested end to end with an honest, stupid signal.

Contract per v0.2 spec:
  - must emit horizon_minutes
  - must emit expected_signed_return (directional, not absolute)
  - must emit expected_volatility
  - must not set size, leverage, or stop
"""
from __future__ import annotations

import statistics

from core.clock import now_utc
from core.types import Candle, Signal

HORIZON_MINUTES = 15
MOMENTUM_LOOKBACK = 15


def predict(candles: list[Candle], symbol: str, source_version: str) -> Signal:
    if len(candles) < MOMENTUM_LOOKBACK + 1:
        return _hold(symbol, source_version)

    closes = [c.close for c in candles[-(MOMENTUM_LOOKBACK + 1):]]
    change = closes[-1] / closes[0] - 1.0

    direction = 1 if change > 0 else -1 if change < 0 else 0
    # Naive confidence: magnitude scaled by a reference of 0.5%.
    confidence = min(1.0, abs(change) / 0.005)

    # Expected signed return: scale momentum by the horizon/lookback ratio.
    # This is a placeholder, deliberately simple, and will lose to costs often.
    expected_signed_return = change * (HORIZON_MINUTES / MOMENTUM_LOOKBACK)

    returns = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes))]
    expected_volatility = statistics.pstdev(returns) if len(returns) > 1 else 0.0

    return Signal(
        decision_time=now_utc(),
        symbol=symbol,
        horizon_minutes=HORIZON_MINUTES,
        direction=direction,
        confidence=confidence,
        expected_signed_return=expected_signed_return,
        expected_volatility=expected_volatility,
        source_version=source_version,
    )


def _hold(symbol: str, source_version: str) -> Signal:
    return Signal(
        decision_time=now_utc(),
        symbol=symbol,
        horizon_minutes=HORIZON_MINUTES,
        direction=0,
        confidence=0.0,
        expected_signed_return=0.0,
        expected_volatility=0.0,
        source_version=source_version,
    )


def predict_features(f) -> Signal:
    """Feature-based version of the momentum baseline.

    Kept deliberately equivalent in spirit to the candle-based version:
    direction from returns_15m, magnitude from its absolute value.
    """
    change = f.returns_15m
    direction = 1 if change > 0 else -1 if change < 0 else 0
    confidence = min(1.0, abs(change) / 0.005)
    expected = change * 1.0  # placeholder, same horizon ratio
    expected = max(-0.02, min(0.02, expected))
    return Signal(
        decision_time=f.decision_time,
        symbol=f.symbol,
        horizon_minutes=15,
        direction=direction,
        confidence=confidence,
        expected_signed_return=expected,
        expected_volatility=max(0.001, f.volatility_15m),
        source_version="momentum-features-v0.2.0",
    )