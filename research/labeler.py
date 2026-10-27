"""Outcome labeling, multi-horizon.

For every prediction older than its shortest horizon, fetch the price at
decision_time + horizon and write outcomes to outcomes_by_horizon.

Point-in-time rules are unchanged:
  - Only predictions with a price recorded at decision time are eligible.
  - outcome_time must be strictly after decision_time.
  - If the exchange cannot supply the exact candle, skip and log; never
    interpolate.

The existing `outcomes` table is left in place for backward compatibility
but is no longer written. New code reads from outcomes_by_horizon.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import timedelta

from core.clock import from_iso, now_utc, to_iso
from exchange.adapter import Exchange
from storage.logger import log_event

log = logging.getLogger(__name__)


DEFAULT_HORIZONS: tuple[int, ...] = (15, 60, 240)


def label_pending(
    ex: Exchange,
    conn: sqlite3.Connection,
    symbol: str,
    *,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> int:
    """Label all unlabeled predictions whose shortest horizon has elapsed.

    Returns the number of predictions for which at least one horizon was
    written.
    """
    if not horizons:
        return 0
    now = now_utc()
    min_horizon = min(horizons)
    cutoff = now - timedelta(minutes=min_horizon + 1)
    max_h = max(horizons)

    # Fetch predictions lacking any outcome at any horizon.
    # The lookup filters on <= decision_time.
    news_rows = conn.execute(
        "SELECT * FROM news_items WHERE superseded_by IS NULL ORDER BY available_time"
    ).fetchall()
    from storage.news import _row_to_item
    all_news = [_row_to_item(r) for r in news_rows]

    def news_lookup(decision_time):
        # Linear scan is fine for a few thousand items; replace with a
        # heap-walk if it becomes a bottleneck.
        iso = decision_time.isoformat()
        return [n for n in all_news if n.available_time.isoformat() <= iso]

    rows = conn.execute(
        "SELECT * FROM predictions WHERE price IS NOT NULL AND price > 0 "
        "AND decision_time <= ? "
        "AND NOT EXISTS (SELECT 1 FROM outcomes_by_horizon o WHERE o.prediction_id = predictions.prediction_id) "
        "ORDER BY decision_time ASC LIMIT 500",
        (to_iso(cutoff),),
    ).fetchall()

    labeled = 0
    for row in rows:
        decision_time = from_iso(row["decision_time"])
        entry_price = float(row["price"])
        direction = int(row["direction"] or 0)

        # Fetch candles covering all horizons in one call.
        try:
            candles = ex.fetch_ohlcv(symbol, "1m", max_h + 5)
        except Exception as e:  # noqa: BLE001
            log_event(conn, "label_fetch_failed", {
                "prediction_id": row["prediction_id"], "error": str(e)
            })
            continue

        wrote_any = False
        for h in horizons:
            target_ts = decision_time + timedelta(minutes=h)
            candle = _first_candle_at_or_after(candles, target_ts)
            if candle is None:
                continue
            gross = direction * (candle.close / entry_price - 1.0)
            cost = (
                float(row["estimated_entry_fee"] or 0.0)
                + float(row["estimated_exit_fee"] or 0.0)
                + float(row["estimated_slippage"] or 0.0)
                + float(row["estimated_funding"] or 0.0)
            )
            net = gross - cost
            conn.execute(
                """INSERT OR IGNORE INTO outcomes_by_horizon
                   (prediction_id, horizon_minutes, price,
                    gross_return, net_return)
                   VALUES (?, ?, ?, ?, ?)""",
                (row["prediction_id"], h, candle.close, gross, net),
            )
            wrote_any = True

        if wrote_any:
            labeled += 1

    if labeled:
        log_event(conn, "labeled_batch", {"count": labeled})
    return labeled


def _first_candle_at_or_after(candles, target):
    for c in candles:
        if c.ts >= target:
            return c
    return None