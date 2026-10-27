"""Order manager.

The only component that talks to the exchange for trading. Every method here
is designed to leave the system in a *safe* state on every failure path.

The invariant: an open position always has a verified protective stop, or the
system is in the process of closing and halting.
"""
from __future__ import annotations

import logging
from typing import Any

from config import Config
from core.clock import now_utc
from core.errors import Halt
from core.types import Approve, MarketMeta, Position
from exchange.adapter import Exchange
from execution.stops import cancel_stop, place_protective_stop
from storage.logger import log_event
from storage.trades import add_fees, close_trade, get_trade_by_prediction, open_trade

log = logging.getLogger(__name__)


def open_position(
    ex: Exchange,
    cfg: Config,
    conn: Any,
    decision: Approve,
    prediction_id: str,
    meta: MarketMeta,
) -> Position:
    """Open a position with a verified protective stop.

    On any failure after entry: reduce-only close and halt.

    Sequence:
      1. Set leverage and isolated margin.
      2. Submit market entry.
      3. Confirm fill (id, filled qty, avg price).
      4. Place protective stop for the confirmed qty.
      5. Verify stop is live.
      6. Write trade row and return Position.
    """
    plan = decision.plan

    # 1. Leverage + isolated margin. CcxtExchange sets isolated internally.
    try:
        ex.set_leverage(cfg.symbol, plan.leverage)
    except Exception as e:
        raise Halt(f"set_leverage failed: {e}") from e

    # 2. Entry.
    try:
        entry = ex.create_market_order(
            cfg.symbol, plan.side, plan.quantity, reduce_only=False
        )
    except Exception as e:
        raise Halt(f"entry order failed: {e}") from e

    entry_id = entry.get("id")
    if not entry_id:
        raise Halt(f"entry returned no id: {entry}")

    # 3. Confirm fill.
    try:
        fill = ex.fetch_order(entry_id, cfg.symbol)
    except Exception as e:
        # We may have a live position with no idea of its state. Halt and
        # let reconciliation resolve it.
        log_event(conn, "entry_fill_fetch_failed", {"entry_id": entry_id, "error": str(e)})
        raise Halt(f"cannot confirm entry fill: {e}") from e

    filled_qty = float(fill.get("filled") or 0.0)
    avg_price = float(fill.get("average") or 0.0)
    if filled_qty <= 0 or avg_price <= 0:
        raise Halt(f"entry {entry_id} not filled: qty={filled_qty} price={avg_price}")

    position_side = "long" if plan.side == "buy" else "short"

    # 4. Stop.
    try:
        stop = place_protective_stop(
            ex, cfg.symbol, position_side, filled_qty, plan.stop_price
        )
    except Halt as e:
        # Critical: we have an open position without verified protection.
        log_event(conn, "stop_placement_failed", {
            "entry_id": entry_id, "filled_qty": filled_qty, "error": str(e)
        })
        _emergency_reduce_only_close(ex, cfg, conn, position_side, filled_qty)
        raise Halt(f"stop placement failed; emergency close attempted: {e}") from e

    stop_id = stop.get("id")

    # PHASE 4: write the trade row now that protection is verified.
    target_distance_pct = 2.0 * plan.stop_distance_pct
    trade = open_trade(
        conn,
        prediction_id=prediction_id,
        symbol=cfg.symbol,
        side=position_side,
        quantity=filled_qty,
        entry_price=avg_price,
        plan=decision.plan,
        target_distance_pct=target_distance_pct,
    )
    # Entry taker fee on the actual filled notional.
    entry_fee = meta.fees.taker * filled_qty * avg_price
    add_fees(conn, trade.trade_id, entry_fee)

    from typing import Literal, cast
    position = Position(
        symbol=cfg.symbol,
        side=cast("Literal['long', 'short']", position_side),
        quantity=filled_qty,
        entry_price=avg_price,
        opened_at=now_utc(),
        stop_order_id=stop_id,
        entry_order_id=entry_id,
        prediction_id=prediction_id,
        stop_distance_pct=plan.stop_distance_pct,
        target_distance_pct=target_distance_pct,
    )

    log_event(conn, "position_opened", {
        "entry_id": entry_id,
        "stop_id": stop_id,
        "trade_id": trade.trade_id,
        "side": position_side,
        "qty": filled_qty,
        "entry_price": avg_price,
        "stop_price": plan.stop_price,
        "prediction_id": prediction_id,
    })
    return position


def close_position(
    ex: Exchange,
    cfg: Config,
    conn: Any,
    position: Position,
    reason: str,
    meta: MarketMeta,
) -> float:
    """Close a position reduce-only, cancel its stop, log the result.

    Returns the exit price (best effort).
    """
    # Cancel stop first so we don't get a race where the stop fills after
    # we've already market-closed.
    if position.stop_order_id:
        try:
            cancel_stop(ex, cfg.symbol, position.stop_order_id)
        except Exception as e:  # noqa: BLE001
            log_event(conn, "stop_cancel_failed", {
                "stop_id": position.stop_order_id, "error": str(e)
            })

    exit_side = "sell" if position.side == "long" else "buy"
    try:
        out = ex.create_market_order(
            cfg.symbol, exit_side, position.quantity, reduce_only=True
        )
    except Exception as e:
        log_event(conn, "exit_order_failed", {"error": str(e)})
        raise Halt(f"exit order failed: {e}") from e

    exit_price = float(out.get("average") or out.get("price") or 0.0)
    if exit_price <= 0:
        raise Halt("exit returned no price")

    trade = get_trade_by_prediction(conn, position.prediction_id) if position.prediction_id else None
    exit_fee = meta.fees.taker * position.quantity * exit_price

    realized = None
    if trade is not None and trade.closed_at is None:
        realized = close_trade(
            conn,
            trade_id=trade.trade_id,
            exit_price=exit_price,
            fees=exit_fee,
            funding=0.0,  # funding is applied separately and already in ledger
            close_reason=reason,
        )
    else:
        if trade:
            add_fees(conn, trade.trade_id, exit_fee)

    log_event(conn, "position_closed", {
        "reason": reason,
        "exit_id": out.get("id"),
        "exit_price": exit_price,
        "trade_id": trade.trade_id if trade else None,
        "realized_pnl": realized,
    })
    return exit_price


def _emergency_reduce_only_close(
    ex: Exchange, cfg: Config, conn: Any, position_side: str, quantity: float
) -> None:
    """Attempt a reduce-only market exit. Never raises; logs everything."""
    exit_side = "sell" if position_side == "long" else "buy"
    try:
        out = ex.create_market_order(cfg.symbol, exit_side, quantity, reduce_only=True)
        log_event(conn, "emergency_close_sent", {
            "exit_id": out.get("id"), "qty": quantity
        })
    except Exception as e:  # noqa: BLE001
        log_event(conn, "emergency_close_failed", {"error": str(e)})