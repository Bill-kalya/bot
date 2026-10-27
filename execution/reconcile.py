"""Reconcile local state against exchange state.

Rules:
  - Exchange is authoritative for positions and orders.
  - Every open position must have exactly one live protective stop.
  - Every live stop must correspond to an open position.
  - Any mismatch → Halt.
"""
from __future__ import annotations

import logging
from typing import Any

from config import Config
from core.errors import Halt
from core.types import Position
from exchange.adapter import Exchange
from storage.logger import log_event

log = logging.getLogger(__name__)


def reconcile(ex: Exchange, cfg: Config, conn: Any) -> list[dict[str, Any]]:
    """Reconcile. Returns list of open positions (as exchange dicts).

    Raises Halt on any mismatch that could lead to unintended exposure.
    """
    # In demo mode (shadow/paper trading), the exchange may not support
    # leverage brackets endpoint needed for fetch_positions.
    # Skip reconciliation and return empty since paper executor manages state.
    if cfg.demo:
        log_event(conn, "reconcile_skipped", {"reason": "demo mode"})
        return []
    
    try:
        positions = ex.fetch_positions(cfg.symbol)
        orders = ex.fetch_open_orders(cfg.symbol)
    except Exception as e:
        raise Halt(f"reconciliation fetch failed: {e}") from e

    # Filter to stop orders on our symbol.
    stops = [o for o in orders if o.get("type") in ("STOP_MARKET", "stop_market",
                                                     "STOP", "stop")]

    # 1. Every position must have a stop.
    for pos in positions:
        matching = [s for s in stops if _matches_position(s, pos)]
        if len(matching) == 0:
            log_event(conn, "reconcile_mismatch", {
                "reason": "open position without protective stop",
                "position": _pos_summary(pos),
            })
            raise Halt("reconcile: open position without protective stop")
        if len(matching) > 1:
            log_event(conn, "reconcile_mismatch", {
                "reason": "multiple stops for one position",
                "position": _pos_summary(pos),
                "stops": [s.get("id") for s in matching],
            })
            raise Halt("reconcile: multiple protective stops for one position")

    # 2. Every stop must correspond to a position.
    for s in stops:
        if not any(_matches_position(s, p) for p in positions):
            log_event(conn, "reconcile_mismatch", {
                "reason": "orphan stop order",
                "stop_id": s.get("id"),
            })
            raise Halt("reconcile: orphan protective stop")

    # 3. Concurrency limit.
    if len(positions) > 1:
        log_event(conn, "reconcile_mismatch", {
            "reason": "multiple open positions",
            "count": len(positions),
        })
        raise Halt("reconcile: more than one open position")

    log_event(conn, "reconcile_ok", {
        "positions": len(positions),
        "stops": len(stops),
    })
    return [
        {
            "side": p.side,
            "quantity": p.quantity,
            "entry_price": p.entry_price,
            "stop_order_id": next(
                (s.get("id") for s in stops if _matches_position(s, p)), None
            ),
        }
        for p in positions
    ]


def _matches_position(stop: dict[str, Any], pos: Position) -> bool:
    """A stop matches a position if it is reduce-only and on the opposite side
    with (approximately) the same quantity."""
    stop_side = (stop.get("side") or "").lower()
    expected_side = "sell" if pos.side == "long" else "buy"
    if stop_side != expected_side:
        return False
    info = stop.get("info", {}) or {}
    if str(stop.get("reduceOnly") or info.get("reduceOnly")).lower() not in ("true", "1"):
        return False
    try:
        stop_qty = float(stop.get("amount") or info.get("origQty") or 0.0)
    except (TypeError, ValueError):
        return False
    return abs(stop_qty - pos.quantity) / max(pos.quantity, 1e-12) < 0.01


def _pos_summary(pos: Position) -> dict[str, Any]:
    return {
        "side": pos.side,
        "quantity": pos.quantity,
        "entry_price": pos.entry_price,
    }


def should_reconcile(loop_index: int, cfg: Config) -> bool:
    if cfg.reconcile_every_loops <= 0:
        return False
    return loop_index > 0 and loop_index % cfg.reconcile_every_loops == 0