import pytest

from config import Config
from core.errors import Halt
from main import _assert_paper_only_is_safe


def _cfg(tmp_path, *, paper_only, demo):
    return Config(
        model_version="t", feature_version="t", config_version="t",
        symbol="BTC/USDT:USDT", demo=demo, exchange_id="binance",
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
        shadow_mode=False,
        paper_only=paper_only,
    )


def test_paper_only_demo_combination_is_allowed(tmp_path):
    _assert_paper_only_is_safe(_cfg(tmp_path, paper_only=True, demo=True))


def test_paper_only_mainnet_combination_halts(tmp_path):
    with pytest.raises(Halt):
        _assert_paper_only_is_safe(_cfg(tmp_path, paper_only=True, demo=False))


def test_not_paper_only_is_always_allowed(tmp_path):
    _assert_paper_only_is_safe(_cfg(tmp_path, paper_only=False, demo=True))
    _assert_paper_only_is_safe(_cfg(tmp_path, paper_only=False, demo=False))