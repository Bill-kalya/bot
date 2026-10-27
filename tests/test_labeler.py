from datetime import timedelta

from core.clock import now_utc
from core.types import Candle, RejectDecision, Signal
from research.labeler import label_pending
from storage.db import connect, init_schema
from storage.logger import log_prediction


class _DeterministicExchange:
    """Wraps a FakeExchange but returns candles anchored to a chosen time."""

    def __init__(self, base_ts, prices):
        self._base = base_ts
        self._prices = prices

    def fetch_ohlcv(self, symbol, timeframe, limit):
        out = []
        for i, p in enumerate(self._prices):
            out.append(Candle(ts=self._base + timedelta(minutes=i),
                              open=p, high=p, low=p, close=p, volume=0))
        return out[-limit:]


def test_labeler_rejects_lookahead(tmp_path):
    """A prediction made now must not be labeled until its horizon elapses."""
    conn = connect(tmp_path / "l.sqlite")
    init_schema(conn)

    now = now_utc()
    sig = Signal(
        decision_time=now, symbol="BTC/USDT:USDT", horizon_minutes=15,
        direction=1, confidence=0.9, expected_signed_return=0.005,
        expected_volatility=0.005, source_version="t",
    )
    log_prediction(
        conn, signal=sig, price=60_000.0,
        decision=RejectDecision("test"),
        estimated_entry_fee=0.0005, estimated_exit_fee=0.0005,
        estimated_slippage=0.0005, estimated_funding=0.0002,
        expected_net_trade_return=0.003,
        model_version="t", feature_version="t", config_version="t",
    )

    # The labeler should find nothing: the prediction is too new.
    ex = _DeterministicExchange(now, [60_000.0] * 120)
    n = label_pending(ex, conn, "BTC/USDT:USDT", horizons=(15, 60))
    assert n == 0


def test_labeler_labels_when_due(tmp_path):
    conn = connect(tmp_path / "l.sqlite")
    init_schema(conn)

    # Prediction made 90 minutes ago.
    decision_time = now_utc() - timedelta(minutes=90)
    sig = Signal(
        decision_time=decision_time, symbol="BTC/USDT:USDT", horizon_minutes=15,
        direction=1, confidence=0.9, expected_signed_return=0.005,
        expected_volatility=0.005, source_version="t",
    )
    log_prediction(
        conn, signal=sig, price=60_000.0,
        decision=RejectDecision("test"),
        estimated_entry_fee=0.0005, estimated_exit_fee=0.0005,
        estimated_slippage=0.0005, estimated_funding=0.0002,
        expected_net_trade_return=0.003,
        model_version="t", feature_version="t", config_version="t",
    )

    # Candles start at decision_time and rise 0.1% per minute.
    prices = [60_000.0 * (1.001 ** i) for i in range(120)]
    ex = _DeterministicExchange(decision_time, prices)
    n = label_pending(ex, conn, "BTC/USDT:USDT", horizons=(15, 60))
    assert n == 1

    row = conn.execute("SELECT * FROM outcomes_by_horizon").fetchone()
    assert row["horizon_minutes"] == 15
    assert row["gross_return"] is not None
    assert row["net_return"] is not None
    assert row["gross_return"] > 0
    # Check 60m horizon also labeled
    row60 = conn.execute("SELECT * FROM outcomes_by_horizon WHERE horizon_minutes = 60").fetchone()
    assert row60 is not None
    assert row60["gross_return"] > row["gross_return"]