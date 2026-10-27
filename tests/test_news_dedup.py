from datetime import UTC, datetime

from config import Config
from data.news.collector import RawNewsItem
from data.news.pipeline import canonical_id, process_one, raw_hash
from storage.db import connect, init_schema


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


def _raw(source_item_id="1"):
    return RawNewsItem(
        source="test", source_item_id=source_item_id,
        url="http://x", title="Bitcoin ETF approved",
        body="The SEC approved a spot Bitcoin ETF.",
        publication_time=datetime(2026, 1, 1, tzinfo=UTC),
        event_time=None, raw_payload=b"payload",
    )


def _cfg(tmp_path):
    return Config(
        model_version="t", feature_version="t", config_version="t",
        symbol="BTC/USDT:USDT", demo=True, exchange_id="binanceusdm",
        start_equity=10.0, ledger_path=tmp_path / "l.sqlite",
        max_leverage=20, max_loss_per_trade_pct=0.20, daily_loss_cap_pct=0.30,
        min_confidence=0.3, min_edge=0.0005,
        slippage_reserve=0.0005, funding_reserve=0.0002,
        latency_reserve=0.0002, stop_slippage_reserve=0.001,
        loop_seconds=1, candle_limit=60,
        stop_file=tmp_path / "STOP", state_dir=tmp_path,
        reconcile_every_loops=20, funding_lookback_hours=24,
        label_every_loops=40,
        news_feeds=[], news_poll_seconds=300,
        strategy_name="momentum", news_lookback_minutes=120,
    )


def test_insert_then_dedup(tmp_path):
    conn = _conn(tmp_path)
    raw = _raw()
    assert process_one(conn, raw, source_reliability=0.5) is True
    assert process_one(conn, raw, source_reliability=0.5) is False
    n = conn.execute("SELECT COUNT(*) AS n FROM news_items").fetchone()["n"]
    assert n == 1


def test_canonical_id_is_stable():
    a = canonical_id("x", "1")
    b = canonical_id("x", "1")
    c = canonical_id("y", "1")
    assert a == b
    assert a != c


def test_raw_hash_matches_input():
    assert raw_hash(b"abc") == raw_hash(b"abc")
    assert raw_hash(b"abc") != raw_hash(b"abd")