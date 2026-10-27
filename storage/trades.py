"""Trade persistence. One row per position, updated on close.

A trade row is created only after a protective stop is verified on the
exchange. This is deliberate: an unprotected position is a bug, not a trade.
"""
from __future__ import annotations

import sqlite3
import uuid

from core.clock import from_iso, now_utc, to_iso
from core.types import Plan, Trade


def open_trade(
    conn: sqlite3.Connection,
    *,
    prediction_id: str,
    symbol: str,
    side: str,
    quantity: float,
    entry_price: float,
    plan: Plan,
    target_distance_pct: float,
) -> Trade:
    trade_id = str(uuid.uuid4())
    now = now_utc()
    notional = quantity * entry_price
    conn.execute(
        """INSERT INTO trades(
            trade_id, prediction_id, symbol, side, quantity, notional, leverage,
            opened_at, entry_price,
            stop_price, stop_distance_pct, target_distance_pct,
            fees_paid, funding_paid
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            trade_id, prediction_id, symbol, side, quantity, notional, plan.leverage,
            to_iso(now), entry_price,
            plan.stop_price, plan.stop_distance_pct, target_distance_pct,
            0.0, 0.0,
        ),
    )
    return Trade(
        trade_id=trade_id,
        prediction_id=prediction_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        notional=notional,
        leverage=plan.leverage,
        opened_at=now,
        closed_at=None,
        entry_price=entry_price,
        exit_price=None,
        stop_price=plan.stop_price,
        stop_distance_pct=plan.stop_distance_pct,
        target_distance_pct=target_distance_pct,
        fees_paid=0.0,
        funding_paid=0.0,
        realized_pnl=None,
        close_reason=None,
    )


def add_fees(conn: sqlite3.Connection, trade_id: str, fees: float) -> None:
    conn.execute(
        "UPDATE trades SET fees_paid = fees_paid + ? WHERE trade_id = ?",
        (fees, trade_id),
    )


def add_funding(conn: sqlite3.Connection, trade_id: str, funding: float) -> None:
    conn.execute(
        "UPDATE trades SET funding_paid = funding_paid + ? WHERE trade_id = ?",
        (funding, trade_id),
    )


def close_trade(
    conn: sqlite3.Connection,
    *,
    trade_id: str,
    exit_price: float,
    fees: float,
    funding: float,
    close_reason: str,
) -> float:
    """Compute and persist realized P&L. Returns the value written."""
    row = conn.execute(
        "SELECT * FROM trades WHERE trade_id = ?", (trade_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"unknown trade_id {trade_id}")
    if row["closed_at"] is not None:
        raise RuntimeError(f"trade {trade_id} already closed")

    direction = 1 if row["side"] == "long" else -1
    gross = direction * (exit_price - row["entry_price"]) * row["quantity"]
    realized = gross - row["fees_paid"] - fees - row["funding_paid"] - funding

    conn.execute(
        """UPDATE trades
           SET closed_at=?, exit_price=?,
               fees_paid = fees_paid + ?,
               funding_paid = funding_paid + ?,
               realized_pnl=?,
               close_reason=?
           WHERE trade_id=?""",
        (
            to_iso(now_utc()), exit_price,
            fees, funding, realized, close_reason, trade_id,
        ),
    )
    return realized


def get_open_trade(conn: sqlite3.Connection):
    row = conn.execute(
        "SELECT * FROM trades WHERE closed_at IS NULL ORDER BY opened_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return _row_to_trade(row)


def get_trade_by_prediction(conn: sqlite3.Connection, prediction_id: str):
    row = conn.execute(
        "SELECT * FROM trades WHERE prediction_id = ? LIMIT 1", (prediction_id,)
    ).fetchone()
    return _row_to_trade(row) if row else None


def _row_to_trade(row) -> Trade:
    return Trade(
        trade_id=row["trade_id"],
        prediction_id=row["prediction_id"],
        symbol=row["symbol"],
        side=row["side"],
        quantity=row["quantity"],
        notional=row["notional"],
        leverage=row["leverage"],
        opened_at=from_iso(row["opened_at"]),
        closed_at=from_iso(row["closed_at"]) if row["closed_at"] else None,
        entry_price=row["entry_price"],
        exit_price=row["exit_price"],
        stop_price=row["stop_price"],
        stop_distance_pct=row["stop_distance_pct"],
        target_distance_pct=row["target_distance_pct"],
        fees_paid=row["fees_paid"],
        funding_paid=row["funding_paid"],
        realized_pnl=row["realized_pnl"],
        close_reason=row["close_reason"],
    )