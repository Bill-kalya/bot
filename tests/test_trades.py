from core.clock import now_utc
from core.types import Plan, RejectDecision, Signal
from storage.db import connect, init_schema
from storage.logger import log_prediction
from storage.trades import (
    add_fees,
    close_trade,
    get_open_trade,
    open_trade,
)


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


def _plan():
    return Plan(
        side="buy", quantity=0.001, notional=60.0, leverage=6,
        stop_price=59_000.0, stop_distance_pct=0.02, worst_case_loss=1.2,
    )


def _insert_prediction(conn) -> str:
    """Insert a dummy prediction row for FK constraint and return its ID."""
    sig = Signal(
        decision_time=now_utc(), symbol="BTC/USDT:USDT", horizon_minutes=15,
        direction=1, confidence=0.9, expected_signed_return=0.005,
        expected_volatility=0.005, source_version="t",
    )
    return log_prediction(
        conn, signal=sig, price=60_000.0,
        decision=RejectDecision("test"),
        estimated_entry_fee=0.0005, estimated_exit_fee=0.0005,
        estimated_slippage=0.0005, estimated_funding=0.0002,
        expected_net_trade_return=0.003,
        model_version="t", feature_version="t", config_version="t",
    )


def _plan():
    return Plan(
        side="buy", quantity=0.001, notional=60.0, leverage=6,
        stop_price=59_000.0, stop_distance_pct=0.02, worst_case_loss=1.2,
    )


def test_open_then_close_round_trip(tmp_path):
    conn = _conn(tmp_path)
    pid = _insert_prediction(conn)
    t = open_trade(
        conn, prediction_id=pid, symbol="BTC/USDT:USDT", side="long",
        quantity=0.001, entry_price=60_000.0, plan=_plan(),
        target_distance_pct=0.04,
    )
    add_fees(conn, t.trade_id, 0.03)
    realized = close_trade(
        conn, trade_id=t.trade_id, exit_price=61_200.0,
        fees=0.0306, funding=0.0001, close_reason="target",
    )
    # long, +2% on 0.001 * 60000 = +1.20 gross, minus ~0.0607 costs.
    assert abs(realized - (1.20 - 0.03 - 0.0306 - 0.0001)) < 1e-9


def test_short_round_trip(tmp_path):
    conn = _conn(tmp_path)
    pid = _insert_prediction(conn)
    t = open_trade(
        conn, prediction_id=pid, symbol="BTC/USDT:USDT", side="short",
        quantity=0.001, entry_price=60_000.0, plan=_plan(),
        target_distance_pct=0.04,
    )
    realized = close_trade(
        conn, trade_id=t.trade_id, exit_price=58_800.0,
        fees=0.03, funding=0.0, close_reason="target",
    )
    # short, -2% move -> +1.20 gross, minus 0.03 fees.
    assert abs(realized - (1.20 - 0.03)) < 1e-9


def test_get_open_trade_returns_most_recent(tmp_path):
    conn = _conn(tmp_path)
    pid1 = _insert_prediction(conn)
    pid2 = _insert_prediction(conn)
    open_trade(conn, prediction_id=pid1, symbol="BTC/USDT:USDT", side="long",
               quantity=0.001, entry_price=60_000.0, plan=_plan(),
               target_distance_pct=0.04)
    t2 = open_trade(conn, prediction_id=pid2, symbol="BTC/USDT:USDT", side="short",
                    quantity=0.001, entry_price=60_000.0, plan=_plan(),
                    target_distance_pct=0.04)
    found = get_open_trade(conn)
    assert found.trade_id == t2.trade_id


def test_double_close_raises(tmp_path):
    import pytest
    conn = _conn(tmp_path)
    pid = _insert_prediction(conn)
    t = open_trade(conn, prediction_id=pid, symbol="BTC/USDT:USDT", side="long",
                   quantity=0.001, entry_price=60_000.0, plan=_plan(),
                   target_distance_pct=0.04)
    close_trade(conn, trade_id=t.trade_id, exit_price=60_100.0,
                fees=0.03, funding=0.0, close_reason="x")
    with pytest.raises(RuntimeError):
        close_trade(conn, trade_id=t.trade_id, exit_price=60_200.0,
                    fees=0.03, funding=0.0, close_reason="x")