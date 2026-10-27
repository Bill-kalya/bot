"""Funding accrual.

Binance settles funding every 8 hours per symbol. We fetch the funding
history, ignore events we've already debited (cursor), and apply the rest
to the ledger. Every applied event is logged so the research layer can
reconcile funding per trade later.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from config import Config
from exchange.adapter import Exchange
from storage.ledger import Ledger
from storage.logger import log_event
from storage.trades import add_funding

log = logging.getLogger(__name__)


def apply_funding(
    ex: Exchange,
    cfg: Config,
    ledger: Ledger,
    conn: object,
    *,
    open_trade_id: str | None = None,
) -> float:
    """Fetch and apply all funding events since the last cursor.

    Returns total funding paid (positive = paid) this call.
    """
    cursor_key = f"funding:{cfg.symbol}"
    last_ms_str = ledger.get_cursor(cursor_key)
    if last_ms_str is None:
        since = datetime.now(tz=UTC) - timedelta(
            hours=cfg.funding_lookback_hours
        )
        since_ms = int(since.timestamp() * 1000)
    else:
        # Small overlap in case of exchange ordering; dedup by timestamp.
        since_ms = int(last_ms_str) - 60_000

    try:
        events = ex.fetch_funding_history(cfg.symbol, since_ms=since_ms)
    except Exception as e:  # noqa: BLE001
        # Funding fetch failure is not fatal, but it must be visible.
        log_event(conn, "funding_fetch_failed", {"error": str(e)})
        return 0.0

    if not events:
        return 0.0

    # Normalize: Binance reports funding as a signed "amount". Positive means
    # the account paid; negative means received. We keep that convention.
    applied = 0.0
    newest_ms = int(last_ms_str) if last_ms_str else 0
    for ev in events:
        ts = int(ev.get("timestamp") or 0)
        if ts == 0:
            continue
        if last_ms_str and ts <= int(last_ms_str):
            continue
        amount = float(ev.get("amount") or 0.0)
        if amount == 0.0:
            newest_ms = max(newest_ms, ts)
            continue
        ledger.apply_funding(amount)
        applied += amount
        newest_ms = max(newest_ms, ts)
        if open_trade_id is not None:
            add_funding(conn, open_trade_id, amount)
        log_event(conn, "funding_applied", {
            "timestamp_ms": ts,
            "amount": amount,
            "symbol": cfg.symbol,
            "trade_id": open_trade_id,
        })

    if newest_ms:
        ledger.set_cursor(cursor_key, str(newest_ms))

    return applied