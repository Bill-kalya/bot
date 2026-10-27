from config import Config
from core.clock import now_utc
from core.types import FeeSchedule, MarketMeta, RejectDecision, Signal
from risk.sizing import plan_position, round_up_to_step, smallest_legal_notional


def _meta(**over):
    base = {
        "symbol": "BTC/USDT:USDT", "min_notional": 50.0, "min_quantity": 0.001,
        "quantity_step": 0.001, "tick_size": 0.1, "max_leverage": 125,
        "fees": FeeSchedule(taker=0.0005, maker=0.0002, fetched_at=now_utc()),
        "fetched_at": now_utc(),
    }
    base.update(over)
    return MarketMeta(**base)  # type: ignore


def _sig(direction: int = 1) -> Signal:
    return Signal(
        decision_time=now_utc(), symbol="BTC/USDT:USDT", horizon_minutes=15,
        direction=direction, confidence=0.9,
        expected_signed_return=0.01, expected_volatility=0.005,
        source_version="t",
    )


def _cfg(tmp_path, **over):
    base = {
        "model_version": "t", "feature_version": "t", "config_version": "t",
        "symbol": "BTC/USDT:USDT", "demo": True, "exchange_id": "binanceusdm",
        "start_equity": 10.0, "ledger_path": tmp_path / "l.sqlite",
        "max_leverage": 20, "max_loss_per_trade_pct": 0.20, "daily_loss_cap_pct": 0.30,
        "min_confidence": 0.3, "min_edge": 0.0005,
        "slippage_reserve": 0.0005, "funding_reserve": 0.0002,
        "latency_reserve": 0.0002, "stop_slippage_reserve": 0.001,
        "loop_seconds": 1, "candle_limit": 60,
        "stop_file": tmp_path / "STOP", "state_dir": tmp_path,
        "reconcile_every_loops": 20, "funding_lookback_hours": 24,
        "label_every_loops": 40,
        "news_feeds": [], "news_poll_seconds": 300,
        "strategy_name": "momentum", "news_lookback_minutes": 120,
        "shadow_mode": True,
        "paper_only": True,
    }
    base.update(over)
    return Config(**base)


def test_round_up_to_step():
    assert round_up_to_step(0.0011, 0.001) == 0.002
    assert round_up_to_step(0.001, 0.001) == 0.001


def test_smallest_legal_notional_respects_buffer():
    assert smallest_legal_notional(_meta(), buffer=1.0) == 50.0
    assert smallest_legal_notional(_meta(), buffer=1.05) == 52.5


def test_plan_at_10_equity_60k_price(tmp_path):
    plan = plan_position(_sig(1), 10.0, _meta(), 60_000.0, _cfg(tmp_path))
    assert not isinstance(plan, RejectDecision)
    assert plan.side == "buy"
    assert plan.notional >= 50.0
    assert plan.leverage == 6  # 52.5 / 10 -> ceil = 6


def test_reject_when_leverage_exceeds_ceiling(tmp_path):
    plan = plan_position(_sig(1), 10.0, _meta(), 60_000.0, _cfg(tmp_path, max_leverage=5))
    assert isinstance(plan, RejectDecision)
    assert "leverage" in plan.reason


def test_reject_non_positive_equity(tmp_path):
    plan = plan_position(_sig(1), 0.0, _meta(), 60_000.0, _cfg(tmp_path))
    assert isinstance(plan, RejectDecision)


def test_reject_non_positive_price(tmp_path):
    plan = plan_position(_sig(1), 10.0, _meta(), 0.0, _cfg(tmp_path))
    assert isinstance(plan, RejectDecision)