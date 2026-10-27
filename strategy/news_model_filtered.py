"""News strategy with regime filter, v0.4.0.

Fires on news sentiment (same rule as news_model.py), but only when the
market is in one of the allowed regimes.

Hypothesis: the news signal is real but masked by averaging across regimes.
If this is true, filtering to high-volatility regimes will produce a
higher hit rate on both 30-day samples.

DO NOT iterate on the allowed regimes after seeing the result. The set
was chosen before the experiment. If it does not work, that is the
finding.
"""
from __future__ import annotations

from core.types import FeatureVector, Signal

MODEL_VERSION = "news-filtered-v0.4.0"
HORIZON_MINUTES = 60
MAX_EXPECTED_RETURN = 0.02

# Allowed regimes. Chosen before the experiment, not tuned after.
ALLOWED_REGIMES = frozenset({"high_vol_chop", "high_vol_trend"})


def predict(features: FeatureVector) -> Signal:
    if features.regime not in ALLOWED_REGIMES:
        return _hold(features)

    news_dir = _news_direction(features)
    if news_dir == 0:
        return _hold(features)

    news_strength = min(
        1.0,
        abs(features.news_relevance_weighted_sentiment_15m) / 0.5,
    )

    expected = news_dir * 0.003 * news_strength
    expected = max(-MAX_EXPECTED_RETURN, min(MAX_EXPECTED_RETURN, expected))

    confidence = min(
        1.0,
        news_strength * (0.5 + 0.5 * min(1.0, features.news_count_15m / 3)),
    )

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
    if s > 0.1:
        return 1
    if s < -0.1:
        return -1
    return 0


def _hold(f) -> Signal:
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