"""If the process is killed after entry but before the protective stop is
verified, the position must be reduce-only closed. This test asserts that
open_position attempts an emergency close and raises Halt."""
from pathlib import Path

import pytest

from config import Config
from core.errors import Halt
from core.types import Approve, Plan
from exchange.fake_adapter import default_fake_meta
from execution.orders import open_position
from storage.db import connect, init_schema


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


def _decision(qty=0.001, stop=59_000.0) -> Approve:
    return Approve(Plan(
        side="buy", quantity=qty, notional=qty * 60_000.0,
        leverage=6, stop_price=stop, stop_distance_pct=0.02,
        worst_case_loss=1.0,
    ))


def _cfg():
    state = Path("/tmp/test_crash_state")
    state.mkdir(exist_ok=True)
    return Config(
        model_version="t", feature_version="t", config_version="t",
        symbol="BTC/USDT:USDT", demo=True, exchange_id="binanceusdm",
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


class MockExchange:
    """Minimal exchange that tracks calls and simulates entry fill + stop failure."""
    def __init__(self) -> None:
        self.market_calls: list[dict[str, object]] = []
        self.stop_calls: list[dict[str, object]] = []
        self.order_id = 1
        self._position: object | None = None

    def load_markets(self) -> None:
        pass

    def fetch_market_meta(self, symbol: str):
        return default_fake_meta(symbol)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int):
        return []

    def fetch_price(self, symbol: str):
        return 60_000.0

    def fetch_positions(self, symbol: str):
        if self._position:
            return [self._position]
        return []

    def fetch_open_orders(self, symbol: str):
        return []

    def fetch_order(self, order_id, symbol):
        # Simulate filled entry order
        return {"id": str(order_id), "filled": 0.001, "average": 60_000.0, "status": "closed"}

    def set_leverage(self, symbol: str, leverage: int):
        pass

    def create_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False):
        self.market_calls.append({
            "symbol": symbol, "side": side, "quantity": quantity, "reduce_only": reduce_only
        })
        oid = str(self.order_id)
        self.order_id += 1
        # For entry order (not reduce_only), create a position
        if not reduce_only:
            self._position = type('Pos', (), {
                'side': 'long' if side == 'buy' else 'short',
                'quantity': quantity,
                'entry_price': 60_000.0
            })()
        return {"id": oid, "symbol": symbol, "side": side, "type": "market",
                "amount": quantity, "price": 60_000.0, "status": "closed",
                "reduceOnly": reduce_only}

    def create_stop_market(self, symbol: str, side: str, quantity: float, stop_price: float):
        self.stop_calls.append({"symbol": symbol, "side": side, "quantity": quantity, "stop_price": stop_price})
        raise RuntimeError("stop rejected by exchange")

    def cancel_order(self, order_id: str, symbol: str):
        pass


def test_stop_failure_triggers_emergency_close(tmp_path):
    ex = MockExchange()
    ex.load_markets()
    conn = _conn(tmp_path)

    with pytest.raises(Halt):
        open_position(ex, _cfg(), conn, _decision(), prediction_id="p1", meta=default_fake_meta())

    # Two market orders: entry, then emergency reduce-only close.
    assert len(ex.market_calls) == 2, f"Expected 2 market calls, got {len(ex.market_calls)}: {ex.market_calls}"
    assert ex.market_calls[0]["reduce_only"] is False
    assert ex.market_calls[1]["reduce_only"] is True