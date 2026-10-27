"""Compare paper fills against demo fills for the same prediction.

The point is to measure the gap between our simulator's assumptions and the
exchange's actual behaviour. If the gap is bigger than our reserves assumed,
the reserves are wrong and the backtester is unreliable.
"""
from __future__ import annotations

import sqlite3

from core.clock import now_utc, to_iso
from storage.logger import log_event


def record_entry_divergence(
    conn: sqlite3.Connection,
    *,
    prediction_id: str,
    paper_price: float,
    demo_price: float,
    paper_fee: float,
    demo_fee: float,
    demo_latency_ms: int,
) -> None:
    diff = (paper_price - demo_price) / demo_price if demo_price else 0.0
    conn.execute(
        """INSERT INTO divergences(
            prediction_id, recorded_at, kind,
            paper_price, demo_price, price_diff_pct,
            paper_fee, demo_fee, demo_latency_ms, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            prediction_id, to_iso(now_utc()), "entry",
            paper_price, demo_price, diff,
            paper_fee, demo_fee, demo_latency_ms, None,
        ),
    )
    log_event(conn, "divergence_entry", {
        "prediction_id": prediction_id, "diff_pct": diff,
        "demo_latency_ms": demo_latency_ms,
    })


def record_exit_divergence(
    conn: sqlite3.Connection,
    *,
    prediction_id: str,
    paper_price: float,
    demo_price: float,
    paper_fee: float,
    demo_fee: float,
    reason: str,
) -> None:
    diff = (paper_price - demo_price) / demo_price if demo_price else 0.0
    conn.execute(
        """INSERT INTO divergences(
            prediction_id, recorded_at, kind,
            paper_price, demo_price, price_diff_pct,
            paper_fee, demo_fee, demo_latency_ms, notes
        ) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            prediction_id, to_iso(now_utc()), "exit",
            paper_price, demo_price, diff,
            paper_fee, demo_fee, None, reason,
        ),
    )
    log_event(conn, "divergence_exit", {
        "prediction_id": prediction_id, "diff_pct": diff, "reason": reason,
    })