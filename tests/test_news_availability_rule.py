from datetime import UTC, datetime, timedelta

from config import Config
from data.news.collector import RawNewsItem
from data.news.pipeline import process_one
from storage.db import connect, init_schema


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


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


def test_missing_publication_uses_ingestion_time(tmp_path):
    conn = _conn(tmp_path)
    raw = RawNewsItem(
        source="t", source_item_id="1", url="u", title="t", body="b",
        publication_time=None, event_time=None, raw_payload=b"p",
    )
    process_one(conn, raw, source_reliability=0.5)
    row = conn.execute("SELECT available_time, ingested_at FROM news_items").fetchone()
    assert row["available_time"] == row["ingested_at"]


def test_future_publication_time_is_clamped_to_ingestion(tmp_path):
    conn = _conn(tmp_path)
    future = datetime.now(tz=UTC) + timedelta(hours=1)
    raw = RawNewsItem(
        source="t", source_item_id="2", url="u", title="t", body="b",
        publication_time=future, event_time=None, raw_payload=b"p",
    )
    process_one(conn, raw, source_reliability=0.5)
    row = conn.execute("SELECT available_time, ingested_at FROM news_items").fetchone()
    assert row["available_time"] == row["ingested_at"], \
        "future-dated publication must never be trusted"