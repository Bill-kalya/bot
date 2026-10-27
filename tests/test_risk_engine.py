import pytest

from config import Config
from core.clock import now_utc
from core.types import Approve, FeeSchedule, MarketMeta, RejectDecision, Signal
from risk.account import Account
from risk.engine import evaluate


@pytest.fixture
def cfg(tmp_path) -> Config:
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
        shadow_mode=True,
        paper_only=True,
        stop_distance_pct=0.02,
    )


@pytest.fixture
def meta() -> MarketMeta:
    return MarketMeta(
        symbol="BTC/USDT:USDT", min_notional=50.0, min_quantity=0.001,
        quantity_step=0.001, tick_size=0.1, max_leverage=125,
        fees=FeeSchedule(taker=0.0005, maker=0.0002, fetched_at=now_utc()),
        fetched_at=now_utc(),
    )


def _account(**over) -> Account:
    base = {
        "equity": 100.0, "daily_baseline": 100.0, "peak_equity": 100.0, "open_positions": 0
    }
    base.update(over)
    return Account(**base)


def _signal(**over) -> Signal:
    base = {
        "decision_time": now_utc(), "symbol": "BTC/USDT:USDT", "horizon_minutes": 15,
        "direction": 1, "confidence": 0.9,
        "expected_signed_return": 0.01, "expected_volatility": 0.005,
        "source_version": "t",
    }
    base.update(over)
    return Signal(**base)


def test_approves_healthy_signal(cfg: Config, meta: MarketMeta) -> None:
    decision, _ = evaluate(_signal(), _account(), meta, 60_000.0, cfg)
    assert isinstance(decision, Approve)
    assert decision.plan.side == "buy"


def test_rejects_kill_switch(cfg: Config, meta: MarketMeta) -> None:
    cfg.stop_file.write_text("stop")
    decision, _ = evaluate(_signal(), _account(), meta, 60_000.0, cfg)
    assert isinstance(decision, RejectDecision)
    assert "kill switch" in decision.reason


def test_rejects_daily_cap(cfg: Config, meta: MarketMeta) -> None:
    account = _account(equity=6.0, daily_baseline=10.0)  # 40% loss
    decision, _ = evaluate(_signal(), account, meta, 60_000.0, cfg)
    assert isinstance(decision, RejectDecision)
    assert "daily loss" in decision.reason


def test_rejects_concurrent_position(cfg: Config, meta: MarketMeta) -> None:
    account = _account(open_positions=1)
    decision, _ = evaluate(_signal(), account, meta, 60_000.0, cfg)
    assert isinstance(decision, RejectDecision)
    assert "already open" in decision.reason


def test_rejects_low_confidence(cfg: Config, meta: MarketMeta) -> None:
    decision, _ = evaluate(_signal(confidence=0.1), _account(), meta, 60_000.0, cfg)
    assert isinstance(decision, RejectDecision)
    assert "confidence" in decision.reason


def test_rejects_net_edge_too_small(cfg: Config, meta: MarketMeta) -> None:
    # Tiny expected return: cannot cover fees.
    decision, _ = evaluate(
        _signal(expected_signed_return=0.0001), _account(), meta, 60_000.0, cfg
    )
    assert isinstance(decision, RejectDecision)
    assert "net return" in decision.reason


def test_rejects_hold_signal(cfg: Config, meta: MarketMeta) -> None:
    decision, _ = evaluate(_signal(direction=0), _account(), meta, 60_000.0, cfg)
    assert isinstance(decision, RejectDecision)
    assert "hold" in decision.reason


def test_rejects_leverage_ceiling(cfg: Config, meta: MarketMeta) -> None:
    cfg_high_risk = Config(**{**cfg.__dict__, "max_leverage": 1,
                              "strategy_name": "momentum", "news_lookback_minutes": 120})
    decision, _ = evaluate(_signal(), _account(equity=10.0, daily_baseline=10.0), meta, 60_000.0, cfg_high_risk)
    assert isinstance(decision, RejectDecision)
    assert "leverage" in decision.reason


def test_rejects_liquidation_buffer_when_stop_too_wide(cfg: Config, meta: MarketMeta) -> None:
    # Force a wide stop: high stop_distance_pct relative to leverage ceiling.
    cfg_wide = Config(**{**cfg.__dict__, "max_loss_per_trade_pct": 0.9, "max_leverage": 6,
                          "strategy_name": "momentum", "news_lookback_minutes": 120,
                          "stop_distance_pct": 0.20})
    decision, _ = evaluate(_signal(), _account(), meta, 60_000.0, cfg_wide)
    assert isinstance(decision, RejectDecision)


def test_short_with_negative_expected_is_approved(cfg: Config, meta: MarketMeta) -> None:
    decision, _ = evaluate(
        _signal(direction=-1, expected_signed_return=-0.01),
        _account(), meta, 60_000.0, cfg,
    )
    assert isinstance(decision, Approve)
    assert decision.plan.side == "sell"