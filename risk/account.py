"""Immutable account snapshot passed to the risk engine.

The risk engine never touches the ledger directly. It receives a snapshot,
returns a decision, and the caller applies any resulting state change.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    equity: float
    daily_baseline: float
    peak_equity: float
    open_positions: int

    @property
    def daily_loss_pct(self) -> float:
        if self.daily_baseline <= 0:
            return 0.0
        return max(0.0, (self.daily_baseline - self.equity) / self.daily_baseline)

    @property
    def drawdown_pct(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, (self.peak_equity - self.equity) / self.peak_equity)