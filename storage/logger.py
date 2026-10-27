"""Append-only event log + prediction logger. Rejects are data."""
from __future__ import annotations

import json
import sqlite3
import uuid

from core.clock import now_utc, to_iso
from core.types import Decision, Signal


def log_event(conn: sqlite3.Connection, kind: str, payload: dict[str, object] | None = None) -> None:
    conn.execute(
        "INSERT INTO events(event_time, kind, payload) VALUES(?, ?, ?)",
        (to_iso(now_utc()), kind, json.dumps(payload or {})),
    )


def log_prediction(
    conn: sqlite3.Connection,
    *,
    signal: Signal,
    price: float,
    decision: Decision,
    estimated_entry_fee: float,
    estimated_exit_fee: float,
    estimated_slippage: float,
    estimated_funding: float,
    expected_net_trade_return: float,
    model_version: str,
    feature_version: str,
    config_version: str,
) -> str:
    pid = str(uuid.uuid4())
    if hasattr(decision, "reason"):
        risk_decision, rejection_reason = "REJECTED", decision.reason
    else:
        risk_decision, rejection_reason = "APPROVED", None

    conn.execute(
        """INSERT INTO predictions(
            prediction_id, decision_time, symbol, price, horizon_minutes,
            direction, confidence, expected_signed_return, expected_volatility,
            estimated_entry_fee, estimated_exit_fee, estimated_slippage,
            estimated_funding, expected_net_trade_return,
            risk_decision, rejection_reason,
            model_version, feature_version, config_version
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pid, to_iso(signal.decision_time), signal.symbol, price,
            signal.horizon_minutes, signal.direction, signal.confidence,
            signal.expected_signed_return, signal.expected_volatility,
            estimated_entry_fee, estimated_exit_fee, estimated_slippage,
            estimated_funding, expected_net_trade_return,
            risk_decision, rejection_reason,
            model_version, feature_version, config_version,
        ),
    )
    return pid