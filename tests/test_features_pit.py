from datetime import UTC, datetime, timedelta

import pytest

from core.types import Candle, NewsItem
from data.features import build_features


def _candles(n, start, price=60_000.0):
    out = []
    for i in range(n):
        p = price + i * 1.0
        out.append(Candle(ts=start + timedelta(minutes=i),
                          open=p, high=p + 5, low=p - 5, close=p, volume=1.0))
    return out


def _news(available, news_id="n1", sentiment=0.5):
    return NewsItem(
        news_id=news_id, source="t", source_item_id=news_id, url="u",
        title="t", body="b", event_time=None,
        available_time=available, ingested_at=available,
        raw_hash="h", scorer_version="v",
        sentiment=sentiment, relevance=0.8, event_type="other",
        source_reliability=0.5, superseded_by=None,
    )


def test_rejects_candle_after_decision_time():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    candles = _candles(30, t0)
    decision_time = t0 + timedelta(minutes=25)  # before last candle
    with pytest.raises(ValueError, match="look-ahead"):
        build_features(candles, [], decision_time, "BTC/USDT:USDT")


def test_rejects_news_after_decision_time():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    candles = _candles(30, t0)
    decision_time = t0 + timedelta(minutes=29)
    future = decision_time + timedelta(seconds=1)
    with pytest.raises(ValueError, match="look-ahead"):
        build_features(candles, [_news(future)], decision_time, "BTC/USDT:USDT")


def test_news_within_window_is_included():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    candles = _candles(30, t0)
    decision_time = candles[-1].ts
    n = _news(decision_time - timedelta(minutes=5))
    fv = build_features(candles, [n], decision_time, "BTC/USDT:USDT")
    assert fv.news_count_15m == 1
    assert fv.news_count_60m == 1


def test_news_outside_window_excluded():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    candles = _candles(30, t0)
    decision_time = candles[-1].ts
    old = _news(decision_time - timedelta(hours=3))
    fv = build_features(candles, [old], decision_time, "BTC/USDT:USDT")
    assert fv.news_count_15m == 0
    assert fv.news_count_60m == 0