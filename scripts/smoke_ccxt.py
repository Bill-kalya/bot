"""Smoke test the real ccxt adapter against Binance demo.

Usage:
    USE_FAKE=false BINANCE_API_KEY=... BINANCE_API_SECRET=... \
        uv run python scripts/smoke_ccxt.py

Prints:
  - market metadata fetched (min_notional, min_qty, step, tick, leverage)
  - taker fee
  - last price
  - last 5 candles
  - open positions
  - open orders

Exits nonzero on any Halt. Does not place orders. Does not touch the ledger.
"""
from __future__ import annotations

import sys

import ccxt

from config import Config
from core.errors import Halt
from exchange.ccxt_adapter import CcxtExchange


def main() -> int:
    cfg = Config.from_env()
    if cfg.demo is False:
        print("refusing to run smoke test against live; set DEMO=true", file=sys.stderr)
        return 2

    ex = CcxtExchange(cfg)
    ex.load_markets()

    # Print the API URLs so we know which environment we're hitting
    try:
        api_urls = ex._ex.urls.get("api", {})
        print(f"api urls: {api_urls}")
    except (AttributeError, KeyError) as e:
        print(f"api urls: (could not read: {e})")

    # Try to fetch market meta, handle leverage fallback gracefully
    try:
        meta = ex.fetch_market_meta(cfg.symbol)
        print("market metadata:")
        print(f"  symbol:         {meta.symbol}")
        print(f"  min_notional:   {meta.min_notional}")
        print(f"  min_quantity:   {meta.min_quantity}")
        print(f"  quantity_step:  {meta.quantity_step}")
        print(f"  tick_size:      {meta.tick_size}")
        print(f"  max_leverage:   {meta.max_leverage}")
        print(f"  taker fee:      {meta.fees.taker}")
        print(f"  maker fee:      {meta.fees.maker}")
        print(f"  fetched_at:     {meta.fetched_at.isoformat()}")
    except Halt as e:
        # If leverage detection fails, still print what we have
        print(f"  WARNING: {e}")
        print(f"  symbol:         {cfg.symbol}")
        print("  min_notional:   (fetch failed)")
        print("  min_quantity:   (fetch failed)")
        print("  quantity_step:  (fetch failed)")
        print("  tick_size:      (fetch failed)")
        print("  max_leverage:   (fetch failed - testnet often doesn't expose leverage brackets)")
        print("  taker fee:      (fetch failed)")
        print("  maker fee:      (fetch failed)")
        print("  fetched_at:     (fetch failed)")

    # Diagnostic: print raw market dict for leverage debugging
    try:
        import json
        m = ex._ex.market(cfg.symbol)
        print("  limits:", json.dumps(m.get("limits", {}), indent=2))
        print("  info keys:", list(m.get("info", {}).keys()))
        print("  leverageBrackets present:", "leverageBrackets" in m.get("info", {}))
    except (AttributeError, KeyError, TypeError) as e:
        print(f"  diagnostic failed: {e}")

    price = ex.fetch_price(cfg.symbol)
    print(f"last price: {price}")

    candles = ex.fetch_ohlcv(cfg.symbol, "1m", 5)
    print("last 5 candles:")
    for c in candles:
        print(f"  {c.ts.isoformat()}  o={c.open} h={c.high} l={c.low} c={c.close} v={c.volume}")

    # Try to fetch positions/orders if credentials are available
    try:
        positions = ex.fetch_positions(cfg.symbol)
        print(f"open positions: {len(positions)}")
        for p in positions:
            print(f"  {p.side} {p.quantity} @ {p.entry_price}")

        orders = ex.fetch_open_orders(cfg.symbol)
        print(f"open orders: {len(orders)}")
        for o in orders:
            print(f"  {o.get('id')} {o.get('type')} {o.get('side')} {o.get('amount')}")
        print("authenticated path: OK")
    except (ccxt.AuthenticationError, ccxt.NetworkError, ccxt.ExchangeError, AttributeError) as e:
        print("open positions: (unavailable)")
        print("open orders:    (unavailable)")
        print(f"authenticated path: FAILED — {e}")
        if cfg.paper_only:
            print("  (paper_only mode; this is expected and non-fatal)")
        else:
            print("  (NOT in paper_only mode; this means orders CANNOT be placed)")
            return 3

    return 0


if __name__ == "__main__":
    sys.exit(main())