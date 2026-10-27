"""Walk-forward evaluation.

Splits a historical window into non-overlapping test periods. Reports
metrics per period plus a pooled metric. The point: a strategy that works
on one contiguous span may be overfit. A strategy that works across many
non-overlapping spans is more credible.

For Phase 9, the "fit" phase is trivial: our strategies have no trainable
parameters. So this is really a stability check: does the metric hold up
across sub-periods?
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Window:
    index: int
    start_ts: object
    end_ts: object
    start_idx: int
    end_idx: int


def make_windows(candles, n_windows: int, *, min_length: int = 1000) -> list[Window]:
    """Split candles into n_windows non-overlapping windows of ~equal length."""
    total = len(candles)
    if total < n_windows * min_length:
        raise ValueError(
            f"not enough candles for {n_windows} windows of {min_length}: "
            f"{total} total"
        )
    size = total // n_windows
    windows = []
    for i in range(n_windows):
        start = i * size
        end = (i + 1) * size if i < n_windows - 1 else total
        windows.append(Window(
            index=i,
            start_ts=candles[start].ts,
            end_ts=candles[end - 1].ts,
            start_idx=start,
            end_idx=end,
        ))
    return windows