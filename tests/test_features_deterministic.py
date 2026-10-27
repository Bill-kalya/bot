from datetime import UTC, datetime, timedelta

from core.types import Candle, NewsItem
from data.features import build_features


def _mk_inputs():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    candles = [
        Candle(ts=t0 + timedelta(minutes=i), open=60_000 + i, high=60_010 + i,
               low=59_990 + i, close=60_005 + i, volume=1.0)
        for i in range(70)
    ]
    news = [
        NewsItem(
            news_id=f"n{i}", source="t", source_item_id=str(i), url="u",
            title="t", body="b", event_time=None,
            available_time=t0 + timedelta(minutes=i),
            ingested_at=t0 + timedelta(minutes=i),
            raw_hash="h", scorer_version="v", sentiment=0.1,
            relevance=0.5, event_type="other", source_reliability=0.5,
            superseded_by=None,
        )
        for i in range(0, 70, 10)
    ]
    return candles, news


def test_same_inputs_same_features():
    candles, news = _mk_inputs()
    dt = candles[-1].ts
    a = build_features(candles, news, dt, "BTC/USDT:USDT")
    b = build_features(candles, news, dt, "BTC/USDT:USDT")
    assert a == b