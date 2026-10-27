from core.clock import now_utc
from core.types import Approve, FeeSchedule, MarketMeta, Plan
from execution.paper import PaperExecutor
from storage.db import connect, init_schema


def _meta():
    return MarketMeta(
        symbol="BTC/USDT:USDT", min_notional=50.0, min_quantity=0.001,
        quantity_step=0.001, tick_size=0.1, max_leverage=125,
        fees=FeeSchedule(taker=0.0005, maker=0.0002, fetched_at=now_utc()),
        fetched_at=now_utc(),
    )


def _plan():
    return Plan(
        side="buy", quantity=0.001, notional=60.0, leverage=6,
        stop_price=58_800.0, stop_distance_pct=0.02, worst_case_loss=1.2,
    )


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


def _cfg(tmp_path):
    from config import Config
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
        strategy_name="news", news_lookback_minutes=120,
        shadow_mode=True,
        paper_only=True,
    )


def test_paper_entry_then_target_close(tmp_path):
    conn = _conn(tmp_path)
    ex = type("E", (), {})()  # unused
    p = PaperExecutor(_cfg(tmp_path), _meta(), ex, conn, equity=10.0,
                      slippage_reserve=0.0005, funding_reserve_per_8h=0.0)

    p.submit_entry(Approve(_plan()), "pred-1")
    p.tick(60_000.0)  # entry fills

    # Price rises above target (entry * 1.04 = 62431.2).
    p.tick(62_500.0)
    row = conn.execute("SELECT * FROM paper_trades").fetchone()
    assert row["exit_price"] is not None
    assert row["close_reason"] == "target"
    assert row["realized_pnl"] is not None


def test_paper_ignores_second_entry_while_open(tmp_path):
    conn = _conn(tmp_path)
    p = PaperExecutor(_cfg(tmp_path), _meta(), type("E", (), {})(), conn,
                      equity=10.0, slippage_reserve=0.0005, funding_reserve_per_8h=0.0)
    p.submit_entry(Approve(_plan()), "pred-1")
    p.tick(60_000.0)

    p.submit_entry(Approve(_plan()), "pred-2")
    p.tick(60_500.0)  # ignored

    n = conn.execute("SELECT COUNT(*) AS n FROM paper_trades").fetchone()["n"]
    assert n == 1