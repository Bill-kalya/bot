from datetime import UTC, datetime, timedelta

from config import Config
from core.clock import now_utc
from core.types import Candle, FeeSchedule, MarketMeta, Signal
from research.simulator import HistoricalSimulator


def _candle(ts, o, h, l, c):
    return Candle(ts=ts, open=o, high=h, low=l, close=c, volume=1.0)


def _meta():
    return MarketMeta(
        symbol="BTC/USDT:USDT", min_notional=50.0, min_quantity=0.001,
        quantity_step=0.001, tick_size=0.1, max_leverage=125,
        fees=FeeSchedule(taker=0.0005, maker=0.0002, fetched_at=now_utc()),
        fetched_at=now_utc(),
    )


def _cfg(tmp_path, exit_mode="fixed_horizon", hold=60):
    return Config(
        model_version="t", feature_version="t", config_version="t",
        symbol="BTC/USDT:USDT", demo=True, exchange_id="binanceusdm",
        start_equity=100.0, ledger_path=tmp_path / "l.sqlite",
        max_leverage=20, max_loss_per_trade_pct=0.20, daily_loss_cap_pct=0.30,
        min_confidence=0.3, min_edge=0.0005,
        slippage_reserve=0.0005, funding_reserve=0.0002,
        latency_reserve=0.0002, stop_slippage_reserve=0.001,
        loop_seconds=1, candle_limit=60,
        stop_file=tmp_path / "STOP", state_dir=tmp_path,
        reconcile_every_loops=20, funding_lookback_hours=24,
        label_every_loops=40, news_feeds=[], news_poll_seconds=300,
        strategy_name="news", news_lookback_minutes=120,
        shadow_mode=False, paper_only=True,
        exit_mode=exit_mode, hold_minutes=hold, regime_filter_enabled=False,
    )


def test_fixed_horizon_closes_after_hold_minutes(tmp_path):
    cfg = _cfg(tmp_path, exit_mode="fixed_horizon", hold=10)
    meta = _meta()
    sim = HistoricalSimulator(cfg, meta, slippage_reserve=0.001,
                              funding_reserve_per_8h=0.0)

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    window = [_candle(t0 - timedelta(minutes=1), 60_000, 60_010, 59_990, 60_000)]

    def factory(_):
        return Signal(
            decision_time=now_utc(), symbol="BTC/USDT:USDT", horizon_minutes=10,
            direction=1, confidence=0.9, expected_signed_return=0.01,
            expected_volatility=0.005, source_version="t",
        )

    # Decision at t0-1, fill at t0 open.
    t1 = _candle(t0, 60_000, 60_010, 59_990, 60_010)
    sim.step(window, factory)
    sim.step_next(t1, factory)
    assert sim.open_trade is not None

    # Advance 10 minutes; fixed_horizon should close.
    t10 = _candle(t0 + timedelta(minutes=10), 60_500, 60_600, 60_400, 60_500)
    sim.step([t1, t10], factory)
    sim.step_next(t10, factory)
    assert sim.open_trade is None
    assert len(sim.result.trades) == 1
    assert sim.result.trades[0].close_reason == "fixed_horizon"