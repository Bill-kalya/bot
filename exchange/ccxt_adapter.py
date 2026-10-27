"""ccxt adapter for Binance USDⓈ-M futures (demo and live).

Everything exchange-specific lives here. Nothing above this file imports ccxt.

Notes:
  - We use the raw ccxt 'binanceusdm' exchange, with sandbox mode toggled by
    cfg.demo. The testnet URL is set via ccxt's set_sandbox_mode(True).
  - Market metadata (min_notional, min_qty, step, tick, leverage tiers) is
    fetched fresh and returned as MarketMeta. No fallback numbers anywhere.
  - Taker fee is read from the exchange's load_markets() response. If it is
    missing, we fail closed. We do not guess 0.0005.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import ccxt

from config import Config
from core.clock import now_utc
from core.errors import Halt
from core.types import Candle, FeeSchedule, MarketMeta, Position

log = logging.getLogger(__name__)


class CcxtExchange:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        opts = {
            "apiKey": _env("BINANCE_API_KEY"),
            "secret": _env("BINANCE_API_SECRET"),
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
                "adjustForTimeDifference": True,
            },
        }
        self._ex = getattr(ccxt, cfg.exchange_id)(opts)
        if cfg.demo:
            self._ex.set_sandbox_mode(True)
        self._markets_loaded = False

    # --- metadata ----------------------------------------------------------

    def load_markets(self) -> None:
        self._ex.load_markets()
        self._markets_loaded = True

    def fetch_market_meta(self, symbol: str) -> MarketMeta:
        if not self._markets_loaded:
            raise Halt("load_markets() must be called before fetch_market_meta()")
        market = self._ex.market(symbol)

        min_notional = _find_filter(market, "minNotional")
        min_qty = _find_filter(market, "minQty")
        step = _find_filter(market, "stepSize")
        tick = _find_filter(market, "tickSize")

        max_lev = _max_leverage(market)
        taker = _taker_fee(market)

        return MarketMeta(
            symbol=symbol,
            min_notional=min_notional,
            min_quantity=min_qty,
            quantity_step=step,
            tick_size=tick,
            max_leverage=int(max_lev),
            fees=FeeSchedule(taker=float(taker), maker=float(market.get("maker", taker)),
                             fetched_at=now_utc()),
            fetched_at=now_utc(),
        )

    # --- market data -------------------------------------------------------

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        raw = self._ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        out: list[Candle] = []
        for row in raw:
            ts_ms = int(row[0])
            ts = datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
            out.append(Candle(
                ts=ts,
                open=float(row[1]), high=float(row[2]), low=float(row[3]),
                close=float(row[4]), volume=float(row[5]),
            ))
        return out

    def fetch_price(self, symbol: str) -> float:
        t = self._ex.fetch_ticker(symbol)
        last = t.get("last") or t.get("close")
        if last is None:
            raise Halt(f"no last price for {symbol}")
        return float(last)

    # --- positions / orders ------------------------------------------------

    def fetch_positions(self, symbol: str) -> list[Position]:
        raw = self._ex.fetch_positions([symbol])
        out: list[Position] = []
        for p in raw:
            contracts = float(p.get("contracts") or 0)
            if contracts == 0:
                continue
            side = p.get("side")
            if side not in ("long", "short"):
                raise Halt(f"unknown position side: {side}")
            out.append(Position(
                symbol=symbol,
                side=side,
                quantity=abs(contracts),
                entry_price=float(p.get("entryPrice") or 0.0),
                opened_at=now_utc(),
                stop_order_id=None,
                entry_order_id=None,
                prediction_id=None,
            ))
        return out

    def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        return self._ex.fetch_open_orders(symbol)  # type: ignore[no-any-return]

    def fetch_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        return self._ex.fetch_order(order_id, symbol)  # type: ignore[no-any-return]

    def fetch_funding_history(
        self, symbol: str, since_ms: int, limit: int = 100
    ) -> list[dict[str, Any]]:
        try:
            return self._ex.fetch_funding_history(
                symbol, since=since_ms, limit=limit
            )  # type: ignore[return-value]
        except Exception as e:
            # Funding fetch failure must not silently zero our accounting.
            # Caller decides whether this is fatal; we surface it clearly.
            raise Halt(f"funding history fetch failed: {e}") from e

    # --- trading -----------------------------------------------------------

    def set_leverage(self, symbol: str, leverage: int) -> None:
        # Isolated margin is a hard requirement; set it here, fail closed.
        try:
            self._ex.set_margin_mode("isolated", symbol)
        except ccxt.ExchangeError as e:
            # Binance errors if margin mode is already isolated; treat as ok.
            if "No need to change margin type" not in str(e):
                raise Halt(f"could not set isolated margin: {e}") from e
        self._ex.set_leverage(leverage, symbol)

    def create_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False) -> dict[str, Any]:
        params = {"reduceOnly": bool(reduce_only)}
        return self._ex.create_order(symbol, "market", side, quantity, None, params)  # type: ignore[no-any-return]

    def create_stop_market(self, symbol: str, side: str, quantity: float, stop_price: float) -> dict[str, Any]:
        params = {
            "stopPrice": stop_price,
            "reduceOnly": True,
            "timeInForce": "GTC",
            "workingType": "MARK_PRICE",
        }
        return self._ex.create_order(symbol, "STOP_MARKET", side, quantity, None, params)  # type: ignore[no-any-return]

    def cancel_order(self, order_id: str, symbol: str) -> None:
        self._ex.cancel_order(order_id, symbol)


# --- helpers ---------------------------------------------------------------

def _env(name: str) -> str:
    import os
    v = os.getenv(name, "")
    return v


def _find_filter(market: dict[str, Any], key: str) -> float:
    for f in market.get("info", {}).get("filters", []):
        if f.get("filterType") == key:
            v = f.get("notional") or f.get("minQty") or f.get("stepSize") or f.get("tickSize")
            if v is not None:
                return float(v)
    # ccxt sometimes exposes these directly on market
    direct = market.get(key)
    if direct is not None:
        return float(direct)
    raise Halt(f"missing required filter {key} for {market.get('symbol')}")


def _max_leverage(market: dict[str, Any]) -> int:
    lev = market.get("limits", {}).get("leverage", {}).get("max")
    if lev:
        return int(lev)
    # Fall back to what the exchange advertises on the symbol.
    info = market.get("info", {})
    brackets = info.get("leverageBrackets") or info.get("brackets")
    if brackets:
        return max(int(b.get("initialLeverage", 1)) for b in brackets if isinstance(b, dict))
    raise Halt(f"cannot determine max leverage for {market.get('symbol')}")


def _taker_fee(market: dict[str, Any]) -> float:
    taker = market.get("taker")
    if taker is None:
        raise Halt(f"exchange did not report taker fee for {market.get('symbol')}")
    return float(taker)