"""Shared test fixtures and helpers."""
from __future__ import annotations

import pytest

from config import Config
from core.clock import now_utc
from core.types import Candle, FeeSchedule, MarketMeta, Plan, Signal


def _base_config_dict(tmp_path):
    """Return a base config dict with all required fields."""
    return {
        "model_version": "t",
        "feature_version": "t",
        "config_version": "t",
        "symbol": "BTC/USDT:USDT",
        "demo": True,
        "exchange_id": "binanceusdm",
        "start_equity": 10.0,
        "ledger_path": tmp_path / "l.sqlite",
        "max_leverage": 20,
        "max_loss_per_trade_pct": 0.20,
        "daily_loss_cap_pct": 0.30,
        "min_confidence": 0.3,
        "min_edge": 0.0005,
        "slippage_reserve": 0.0005,
        "funding_reserve": 0.0002,
        "latency_reserve": 0.0002,
        "stop_slippage_reserve": 0.001,
        "loop_seconds": 1,
        "candle_limit": 60,
        "stop_file": tmp_path / "STOP",
        "state_dir": tmp_path,
        "reconcile_every_loops": 20,
        "funding_lookback_hours": 24,
        "label_every_loops": 40,
        "news_feeds": [],
        "news_poll_seconds": 300,
        "strategy_name": "momentum",
        "news_lookback_minutes": 120,
        "shadow_mode": True,
        "paper_only": True,
    }


@pytest.fixture
def _cfg(tmp_path, request):
    base = _base_config_dict(tmp_path)
    # Allow overriding via test function's kwargs
    over = getattr(request, "param", {})
    base.update(over)
    return Config(**base)


@pytest.fixture
def _meta():
    return MarketMeta(
        symbol="BTC/USDT:USDT", min_notional=50.0, min_quantity=0.001,
        quantity_step=0.001, tick_size=0.1, max_leverage=125,
        fees=FeeSchedule(taker=0.0005, maker=0.0002, fetched_at=now_utc()),
        fetched_at=now_utc(),
    )


@pytest.fixture
def _candle():
    
    def _make(ts, o, h, l, c):
        return Candle(ts=ts, open=o, high=h, low=l, close=c, volume=1.0)
    return _make


@pytest.fixture
def _plan():
    return Plan(
        side="buy", quantity=0.001, notional=60.0, leverage=6,
        stop_price=59_000.0, stop_distance_pct=0.02, worst_case_loss=1.2,
    )


@pytest.fixture
def _signal():
    from core.clock import now_utc
    
    def _make(direction=1, expected=0.01):
        return Signal(
            decision_time=now_utc(),
            symbol="BTC/USDT:USDT",
            horizon_minutes=15,
            direction=direction,
            confidence=0.9,
            expected_signed_return=expected,
            expected_volatility=0.005,
            source_version="t",
        )
    return _make


@pytest.fixture
def _plan():
    return Plan(
        side="buy", quantity=0.001, notional=60.0, leverage=6,
        stop_price=59_000.0, stop_distance_pct=0.02, worst_case_loss=1.2,
    )