"""Protective stop placement and verification.

Rule: a position is not considered open until its stop is verified on the
exchange. If verification fails, the caller must reduce-only close immediately
and halt.
"""
from __future__ import annotations

from typing import Any

from core.errors import Halt
from exchange.adapter import Exchange


def place_protective_stop(
    ex: Exchange,
    symbol: str,
    position_side: str,
    quantity: float,
    stop_price: float,
) -> dict[str, Any]:
    """Place STOP_MARKET and verify it is live on the exchange.

    Returns the exchange order dict on success.
    Raises Halt if the stop cannot be verified.
    """
    # Opposite side of the position.
    order_side = "sell" if position_side == "long" else "buy"

    try:
        order = ex.create_stop_market(symbol, order_side, quantity, stop_price)
    except Exception as e:
        raise Halt(f"stop placement failed: {e}") from e

    order_id = order.get("id")
    if not order_id:
        raise Halt(f"stop placement returned no id: {order}")

    # Verify it exists and is live.
    try:
        verify = ex.fetch_order(order_id, symbol)
    except Exception as e:
        raise Halt(f"stop verification fetch failed for {order_id}: {e}") from e

    status = (verify.get("status") or "").lower()
    if status not in ("open", "new"):
        raise Halt(f"stop {order_id} not live; status={status}")

    # Confirm it is reduce-only and has the expected trigger.
    info = verify.get("info", {}) or {}
    reduce_only = verify.get("reduceOnly") or info.get("reduceOnly")
    if str(reduce_only).lower() not in ("true", "1"):
        raise Halt(f"stop {order_id} is not reduce-only")

    expected_trigger = float(stop_price)
    actual_trigger = float(
        verify.get("stopPrice") or info.get("stopPrice") or 0.0
    )
    if actual_trigger <= 0:
        raise Halt(f"stop {order_id} has no trigger price")
    # Tick-size rounding can move the trigger slightly; allow 1 tick tolerance.
    if abs(actual_trigger - expected_trigger) / expected_trigger > 0.002:
        raise Halt(
            f"stop trigger {actual_trigger} differs from requested {expected_trigger}"
        )

    return verify


def cancel_stop(ex: Exchange, symbol: str, stop_order_id: str) -> None:
    try:
        ex.cancel_order(stop_order_id, symbol)
    except Exception as e:
        # If the stop is already gone (filled or cancelled), that's fine.
        if "Unknown order" in str(e) or "not found" in str(e).lower():
            return
        raise