from pathlib import Path

import pytest

from config import Config
from core.errors import Halt
from exchange.fake_adapter import FakeExchange, default_fake_meta
from execution.reconcile import reconcile
from storage.db import connect, init_schema


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


def _cfg(demo: bool = False):
    state = Path("/tmp/test_reconcile_state")
    state.mkdir(exist_ok=True)
    return Config(
        model_version="t", feature_version="t", config_version="t",
        symbol="BTC/USDT:USDT", demo=demo, exchange_id="binanceusdm",
        start_equity=10.0, ledger_path=state / "l.sqlite",
        max_leverage=20, max_loss_per_trade_pct=0.20, daily_loss_cap_pct=0.30,
        min_confidence=0.3, min_edge=0.0005,
        slippage_reserve=0.0005, funding_reserve=0.0002,
        latency_reserve=0.0002, stop_slippage_reserve=0.001,
        loop_seconds=1, candle_limit=60,
        stop_file=state / "STOP", state_dir=state,
        reconcile_every_loops=20, funding_lookback_hours=24,
        label_every_loops=40,
        news_feeds=[], news_poll_seconds=300,
        strategy_name="momentum", news_lookback_minutes=120,
        shadow_mode=True,
        paper_only=True,
    )


def test_reconcile_ok_when_flat(tmp_path):
    ex = FakeExchange(default_fake_meta())
    ex.load_markets()
    conn = _conn(tmp_path)
    positions = reconcile(ex, _cfg(demo=False), conn)
    assert positions == []


def test_reconcile_halts_on_orphan_stop(tmp_path):
    ex = FakeExchange(default_fake_meta())
    ex.load_markets()
    conn = _conn(tmp_path)
    # Create a stop with no corresponding position.
    ex.create_stop_market("BTC/USDT:USDT", "sell", 0.001, 59_000.0)
    with pytest.raises(Halt):
        reconcile(ex, _cfg(demo=False), conn)