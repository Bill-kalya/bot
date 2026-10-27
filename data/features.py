"""Feature engine.

Builds a FeatureVector from:
  - candles up to and including decision_time
  - news items with available_time <= decision_time

Never touches data after decision_time. Never forward-fills. Never
interpolates. If a feature cannot be computed from the inputs, it is set to
a conservative default (usually 0.0) and logged.

feature_version is bumped whenever the definition of any feature changes.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from core.types import Candle, FeatureVector, NewsItem

FEATURE_VERSION = "features-v0.2.0"


def build_features(
    candles: list[Candle],
    news: list[NewsItem],
    decision_time: datetime,
    symbol: str,
    *,
    feature_version: str = FEATURE_VERSION,
) -> FeatureVector:
    """Build one FeatureVector.

    Preconditions (enforced, not assumed):
      - candles[-1].ts <= decision_time
      - every news item has available_time <= decision_time
    """
    if not candles:
        raise ValueError("no candles")
    if candles[-1].ts > decision_time:
        raise ValueError("look-ahead: last candle is after decision_time")
    for n in news:
        if n.available_time > decision_time:
            raise ValueError("look-ahead: news available_time after decision_time")

    closes = [c.close for c in candles]
    price = closes[-1]

    r1 = _return(closes, 1)
    r5 = _return(closes, 5)
    r15 = _return(closes, 15)
    r60 = _return(closes, 60)

    v15 = _stdev_returns(closes, 15)
    v60 = _stdev_returns(closes, 60)
    vol_z = _volume_zscore(candles, 60)

    last_range = (
        (candles[-1].high - candles[-1].low) / candles[-1].close
        if candles[-1].close > 0 else 0.0
    )

    above_sma15 = 1.0 if price > _sma(closes, 15) else 0.0
    above_sma60 = 1.0 if price > _sma(closes, 60) else 0.0
    rsi = _rsi(closes, 14)

    # Regime features (Tier 1)
    atr14 = _atr_14(candles)
    vol_pct = _volatility_percentile(candles, 60)
    trend_str = _trend_strength(candles, 60)
    regime = _classify_regime(vol_pct, trend_str)

    n15 = _slice_news(news, decision_time, minutes=15)
    n60 = _slice_news(news, decision_time, minutes=60)

    return FeatureVector(
        decision_time=decision_time,
        symbol=symbol,
        feature_version=feature_version,

        price=price,
        returns_1m=r1, returns_5m=r5, returns_15m=r15, returns_60m=r60,
        volatility_15m=v15, volatility_60m=v60,
        volume_z_60m=vol_z,
        range_pct_last_1m=last_range,
        above_sma_15m=above_sma15,
        above_sma_60m=above_sma60,
        rsi_14=rsi,

        news_count_15m=len(n15),
        news_count_60m=len(n60),
        news_sentiment_mean_15m=_mean_sentiment(n15),
        news_sentiment_mean_60m=_mean_sentiment(n60),
        news_sentiment_max_abs_15m=_max_abs_sentiment(n15),
        news_relevance_weighted_sentiment_15m=_rel_weighted_sentiment(n15),
        news_regulation_flag_60m=_has_event_type(n60, "regulation"),
        news_macro_flag_60m=_has_event_type(n60, "macro"),
        news_listing_flag_60m=_has_event_type(n60, "listing"),

        atr_14=atr14,
        volatility_percentile_60m=vol_pct,
        trend_strength_60m=trend_str,
        regime=regime,
    )


# --- market helpers --------------------------------------------------------

def _return(closes: list[float], n: int) -> float:
    if len(closes) < n + 1 or closes[-n - 1] == 0:
        return 0.0
    return closes[-1] / closes[-n - 1] - 1.0


def _stdev_returns(closes: list[float], n: int) -> float:
    if len(closes) < n + 1:
        return 0.0
    window = closes[-n - 1:]
    rets = [window[i] / window[i - 1] - 1.0 for i in range(1, len(window))]
    return statistics.pstdev(rets) if len(rets) > 1 else 0.0


def _sma(closes: list[float], n: int) -> float:
    if len(closes) < n:
        return closes[-1] if closes else 0.0
    return sum(closes[-n:]) / n


def _volume_zscore(candles: list[Candle], n: int) -> float:
    if len(candles) < n:
        return 0.0
    vols = [c.volume for c in candles[-n:]]
    if len(vols) < 2:
        return 0.0
    mean = statistics.mean(vols)
    sd = statistics.pstdev(vols)
    if sd == 0:
        return 0.0
    return (vols[-1] - mean) / sd


def _rsi(closes: list[float], n: int) -> float:
    """Simple RSI over the last n periods. Returns 50.0 if not enough data."""
    if len(closes) < n + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    window = closes[-(n + 1):]
    for i in range(1, len(window)):
        delta = window[i] - window[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    if gains + losses == 0:
        return 50.0
    rs = gains / losses if losses > 0 else float("inf")
    if rs == float("inf"):
        return 100.0
    return 100.0 - 100.0 / (1.0 + rs)


# --- regime helpers (Tier 1) ----------------------------------------------

def _atr_14(candles: list[Candle]) -> float:
    """Average True Range over 14 candles, normalized by close."""
    if len(candles) < 15:
        return 0.0
    trs = []
    for i in range(len(candles) - 14, len(candles)):
        c = candles[i]
        prev_close = candles[i - 1].close
        tr = max(
            c.high - c.low,
            abs(c.high - prev_close),
            abs(c.low - prev_close),
        )
        trs.append(tr)
    return (sum(trs) / len(trs)) / candles[-1].close if candles[-1].close else 0.0


def _volatility_percentile(candles: list[Candle], n: int = 60) -> float:
    """Where does the current 1-minute return magnitude sit in the last n."""
    if len(candles) < n + 1:
        return 0.5
    returns = []
    for i in range(len(candles) - n, len(candles)):
        prev = candles[i - 1].close
        if prev > 0:
            returns.append(abs(candles[i].close / prev - 1.0))
    if not returns:
        return 0.5
    current = returns[-1]
    below = sum(1 for r in returns if r <= current)
    return below / len(returns)


def _trend_strength(candles: list[Candle], n: int = 60) -> float:
    """Absolute distance from SMA(n), normalized by SMA(n)."""
    if len(candles) < n or candles[-1].close <= 0:
        return 0.0
    sma = sum(c.close for c in candles[-n:]) / n
    if sma <= 0:
        return 0.0
    return abs(candles[-1].close - sma) / sma


def _classify_regime(vol_percentile: float, trend_strength: float) -> str:
    """Split into four regimes. Thresholds are deliberately simple.

    vol_percentile >= 0.7 => high vol, else low vol.
    trend_strength >= 0.005 (0.5%) => trend, else chop.
    """
    high_vol = vol_percentile >= 0.7
    trending = trend_strength >= 0.005
    if high_vol and trending:
        return "high_vol_trend"
    if high_vol and not trending:
        return "high_vol_chop"
    if not high_vol and trending:
        return "low_vol_trend"
    return "low_vol_chop"


# --- news helpers ----------------------------------------------------------

def _slice_news(news: list[NewsItem], decision_time: datetime, minutes: int) -> list[NewsItem]:
    cutoff = decision_time - timedelta(minutes=minutes)
    return [n for n in news if cutoff <= n.available_time <= decision_time]


def _mean_sentiment(items: list[NewsItem]) -> float:
    if not items:
        return 0.0
    return sum(i.sentiment for i in items) / len(items)


def _max_abs_sentiment(items: list[NewsItem]) -> float:
    if not items:
        return 0.0
    return max((abs(i.sentiment) for i in items), default=0.0)


def _rel_weighted_sentiment(items: list[NewsItem]) -> float:
    if not items:
        return 0.0
    num = sum(i.sentiment * i.relevance * i.source_reliability for i in items)
    den = sum(i.relevance * i.source_reliability for i in items)
    if den == 0:
        return 0.0
    return num / den


def _has_event_type(items: list[NewsItem], event_type: str) -> float:
    return 1.0 if any(i.event_type == event_type for i in items) else 0.0