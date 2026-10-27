"""News-only strategy, v0.4.0.

Fires on news sentiment alone, no market agreement required.
Replaces the news+market agreement model (v0.2) which was filtered by
momentum's anti-predictive signal.

Phase 9 finding: News edge exists at 60-minute horizon (57.1% hit rate,
CI [50.3%, 64.4%]), not at 15m. Model updated to 60-minute horizon.
"""
from __future__ import annotations

from core.types import FeatureVector, Signal

MODEL_VERSION = "news-only-v0.4.0"
HORIZON_MINUTES = 60

# Bounds keep a bad feature from producing a wild expectation.
# 60-minute returns are larger than 15m; allow up to 1% expected return.
MAX_EXPECTED_RETURN = 0.01


def predict(features: FeatureVector) -> Signal:
    from core.types import Signal
    # Direction: news sentiment only.
    news_dir = _news_direction(features)

    if news_dir == 0:
        return _hold(features)

    # Magnitude: scaled by relevance-weighted sentiment, bounded.
    news_strength = min(1.0, abs(features.news_relevance_weighted_sentiment_15m) / 0.15)
    strength = news_strength

    expected = news_dir * 0.003 * strength  # 0.30% max at strength=1
    expected = max(-MAX_EXPECTED_RETURN, min(MAX_EXPECTED_RETURN, expected))

    # Confidence capped by news strength and count.
    confidence = min(1.0, strength * (0.5 + 0.5 * min(1.0, features.news_count_15m / 3)))

    # Volatility forecast: realised volatility_15m, with a small floor.
    vol = max(0.001, features.volatility_15m)

    return Signal(
        decision_time=features.decision_time,
        symbol=features.symbol,
        horizon_minutes=HORIZON_MINUTES,
        direction=news_dir,
        confidence=confidence,
        expected_signed_return=expected,
        expected_volatility=vol,
        source_version=MODEL_VERSION,
    )


def _news_direction(f) -> int:
    s = f.news_relevance_weighted_sentiment_15m
    if s > 0.15:
        return 1
    if s < -0.15:
        return -1
    return 0


def _hold(f) -> Signal:
    from core.types import Signal
    return Signal(
        decision_time=f.decision_time,
        symbol=f.symbol,
        horizon_minutes=HORIZON_MINUTES,
        direction=0,
        confidence=0.0,
        expected_signed_return=0.0,
        expected_volatility=max(0.001, f.volatility_15m),
        source_version=MODEL_VERSION,
    )


HORIZON_MINUTES = 60
MAX_EXPECTED_RETURN = 0.01
MODEL_VERSION = "news-only-v0.4.0"