"""Persistent strategy ledger. Equity survives restart. Exchange is authority
for positions; this is the strategy's own accounting of its $10."""
from __future__ import annotations

import sqlite3

from core.clock import now_utc, to_iso


class Ledger:
    def __init__(self, conn: sqlite3.Connection, start_equity: float) -> None:
        self._conn = conn
        if self._get("equity") is None:
            self._set("equity", start_equity)
            self._set("daily_baseline", start_equity)
            self._set("peak_equity", start_equity)

    def _get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM state WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def _set(self, key: str, value: str | float) -> None:
        self._conn.execute(
            "INSERT INTO state(key, value, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at",
            (key, str(value), to_iso(now_utc())),
        )

    @property
    def equity(self) -> float:
        return float(self._get("equity") or 0.0)

    @property
    def daily_baseline(self) -> float:
        return float(self._get("daily_baseline") or 0.0)

    @property
    def peak_equity(self) -> float:
        return float(self._get("peak_equity") or 0.0)

    def drawdown_pct(self) -> float:
        peak = self.peak_equity
        return 0.0 if peak <= 0 else (peak - self.equity) / peak

    def daily_loss_pct(self) -> float:
        base = self.daily_baseline
        return 0.0 if base <= 0 else (base - self.equity) / base

    def apply_realized_pnl(self, delta: float) -> None:
        new_equity = self.equity + delta
        self._set("equity", new_equity)
        if new_equity > self.peak_equity:
            self._set("peak_equity", new_equity)

    def reset_daily_baseline(self) -> None:
        self._set("daily_baseline", self.equity)

    def apply_funding(self, amount_paid: float) -> None:
        """amount_paid > 0 means we paid. Equity decreases."""
        if amount_paid == 0:
            return
        self.apply_realized_pnl(-amount_paid)

    def get_cursor(self, key: str) -> str | None:
        return self._get(f"cursor:{key}")

    def set_cursor(self, key: str, value: str) -> None:
        self._set(f"cursor:{key}", value)