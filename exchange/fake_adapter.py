"""In-memory exchange for Phase 0/1 development.

Deterministic, no network. Deliberately rejects any hard-coded market fact:
you must supply MarketMeta explicitly so tests fail if someone sneaks in a
fallback number.
"""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from core.clock import now_utc
from core.types import Candle, FeeSchedule, MarketMeta, Position


class FakeExchange:
    def __init__(self, meta: MarketMeta) -> None:
        self._meta = meta
        self._price = 60_000.0
        self._positions: list[Position] = []
        self._orders: dict[str, dict[str, object]] = {}
        self._next_order_id = 1

    def load_markets(self) -> None:
        pass

    def fetch_market_meta(self, symbol: str) -> MarketMeta:
        if symbol != self._meta.symbol:
            raise ValueError(f"unknown symbol {symbol}")
        return self._meta

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        # Deterministic synthetic candles around self._price.
        now = now_utc()
        out: list[Candle] = []
        for i in range(limit):
            ts = now - timedelta(minutes=limit - i)
            base = self._price * (1 + 0.0001 * math.sin(i / 5))
            out.append(Candle(ts=ts, open=base, high=base * 1.0005,
                              low=base * 0.9995, close=base, volume=1.0))
        return out

    def fetch_price(self, symbol: str) -> float:
        return self._price

    def fetch_positions(self, symbol: str) -> list[Position]:
        return [p for p in self._positions if p.symbol == symbol]

    def fetch_open_orders(self, symbol: str) -> list[dict[str, object]]:
        return list(self._orders.values())

    def set_leverage(self, symbol: str, leverage: int) -> None:
        if leverage > self._meta.max_leverage:
            raise ValueError("leverage exceeds exchange max")

    def create_market_order(
        self, symbol: str, side: str, quantity: float, reduce_only: bool = False
    ) -> dict[str, object]:
        oid = str(self._next_order_id); self._next_order_id += 1
        order = {"id": oid, "symbol": symbol, "side": side, "type": "market",
                 "amount": quantity, "price": self._price, "status": "closed",
                 "reduceOnly": reduce_only}
        self._orders[oid] = order
        return order

    def create_stop_market(
        self, symbol: str, side: str, quantity: float, stop_price: float
    ) -> dict[str, object]:
        oid = str(self._next_order_id); self._next_order_id += 1
        order = {"id": oid, "symbol": symbol, "side": side, "type": "STOP_MARKET",
                 "amount": quantity, "stopPrice": stop_price, "status": "open",
                 "reduceOnly": True}
        self._orders[oid] = order
        return order

    def fetch_order(self, order_id: str, symbol: str) -> dict[str, object]:
        return self._orders[order_id]

    def cancel_order(self, order_id: str, symbol: str) -> None:
        self._orders.pop(order_id, None)

    def fetch_funding_history(
        self, symbol: str, since_ms: int, limit: int = 100
    ) -> list[dict[str, object]]:
        # Deterministic: one funding event per 8h boundary after since_ms.
        # Small, always-positive (we pay), so tests exercise the debit path.
        eight_h = 8 * 3600 * 1000
        first = ((since_ms // eight_h) + 1) * eight_h
        out: list[dict] = []
        ts = first
        n = 0
        while ts <= _now_ms() and n < limit:
            out.append({
                "timestamp": ts,
                "symbol": symbol,
                "amount": 0.0001,  # paid
                "info": {"fundingRate": "0.00001"},
            })
            ts += eight_h
            n += 1
        return out


def _now_ms() -> int:
    return int(datetime.now(tz=UTC).timestamp() * 1000)


def default_fake_meta(symbol: str = "BTC/USDT:USDT") -> MarketMeta:
    """Explicit, labelled, test-only metadata. Never used against real exchange."""
    return MarketMeta(
        symbol=symbol,
        min_notional=50.0,
        min_quantity=0.001,
        quantity_step=0.001,
        tick_size=0.10,
        max_leverage=125,
        fees=FeeSchedule(taker=0.0005, maker=0.0002, fetched_at=now_utc()),
        fetched_at=now_utc(),
    )