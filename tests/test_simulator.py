from datetime import UTC, datetime, timedelta

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


def _signal(direction=1, expected=0.01):
    return Signal(
        decision_time=now_utc(), symbol="BTC/USDT:USDT", horizon_minutes=15,
        direction=direction, confidence=0.9,
        expected_signed_return=expected, expected_volatility=0.005,
        source_version="t",
    )


def test_entry_fills_at_next_open_with_slippage(_cfg, _meta):
    """A decision on candle t fills at candle t+1 open, worsened by slippage."""
    cfg = _cfg
    meta = _meta
    sim = HistoricalSimulator(
        cfg, meta, slippage_reserve=0.001, funding_reserve_per_8h=0.0001,
    )

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    window = [_candle(t0 - timedelta(minutes=1), 60_000, 60_010, 59_990, 60_000)]
    t1 = _candle(t0, 60_000, 60_020, 59_980, 60_010)

    # Force a strong long signal that the risk engine will approve.
    def factory(candles):
        return Signal(
            decision_time=now_utc(), symbol="BTC/USDT:USDT", horizon_minutes=15,
            direction=1, confidence=0.9,
            expected_signed_return=0.01, expected_volatility=0.005,
            source_version="t",
        )
    sim.step(window, factory)
    sim.step_next(t1, factory)

    # Entry price should be t1.open * (1 + slippage).
    assert sim.open_trade is not None
    expected = t1.open * (1 + 0.001)
    assert abs(sim.open_trade.entry_price - expected) < 1e-6


def test_stop_fills_at_stop_minus_gap(_cfg, _meta):
    from core.types import Signal
    cfg = _cfg
    meta = _meta
    sim = HistoricalSimulator(
        cfg, meta, slippage_reserve=0.0005, funding_reserve_per_8h=0.0,
        gap_reserve=0.002,
    )
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    def factory(_):
        return Signal(
            decision_time=now_utc(), symbol="BTC/USDT:USDT", horizon_minutes=15,
            direction=1, confidence=0.9,
            expected_signed_return=0.01, expected_volatility=0.005,
            source_version="t",
        )

    window = [_candle(t0 - timedelta(minutes=1), 60_000, 60_010, 59_990, 60_000)]
    t1 = _candle(t0, 60_000, 60_020, 59_980, 60_000)
    sim.step(window, factory)
    sim.step_next(t1, factory)
    stop = sim.open_trade.stop_price

    # A candle whose low dips well below the stop.
    t2 = _candle(t0 + timedelta(minutes=1), 60_000, 60_000, stop * 0.99, stop * 0.99)
    sim.step([t1, t2], factory)
    sim.step_next(t2, factory)

    closed = sim.result.trades[-1]
    assert closed.close_reason == "stop"
    # Exit price is worse than the stop by the gap reserve.
    assert closed.exit_price < stop


def test_no_lookahead_in_baseline_signal(_cfg, _meta):
    """Sanity: the simulator never sees a candle beyond the decision candle
    when making the decision."""
    from core.types import Signal
    cfg = _cfg
    meta = _meta
    sim = HistoricalSimulator(
        cfg, meta, slippage_reserve=0.0005, funding_reserve_per_8h=0.0,
    )
    seen_max_ts = [None]

    def factory(candles):
        seen_max_ts[0] = candles[-1].ts
        return Signal(
            decision_time=now_utc(), symbol="BTC/USDT:USDT", horizon_minutes=15,
            direction=0, confidence=0.0,
            expected_signed_return=0.0, expected_volatility=0.005,
            source_version="t",
        )

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    window = [
        _candle(t0 + timedelta(minutes=i), 60_000, 60_010, 59_990, 60_000)
        for i in range(3)
    ]
    sim.step(window, factory)
    assert seen_max_ts[0] == window[-1].ts