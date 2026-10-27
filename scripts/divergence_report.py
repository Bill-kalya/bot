"""Print a summary of paper vs demo divergences.

Usage:
    uv run python scripts/divergence_report.py
"""
from __future__ import annotations

import statistics
import sys

from config import Config
from storage.db import connect


def main() -> int:
    cfg = Config.from_env()
    conn = connect(cfg.ledger_path)

    rows = conn.execute(
        "SELECT * FROM divergences WHERE kind='entry' ORDER BY recorded_at"
    ).fetchall()
    print(f"=== entry divergences (n={len(rows)}) ===")
    if rows:
        diffs = [r["price_diff_pct"] for r in rows]
        lat = [r["demo_latency_ms"] for r in rows if r["demo_latency_ms"] is not None]
        print(f"  mean  price diff: {statistics.mean(diffs):+.5%}")
        print(f"  median price diff: {statistics.median(diffs):+.5%}")
        print(f"  p95 |price diff|:  {_p95_abs(diffs):.5%}")
        print(f"  max |price diff|:  {max(abs(d) for d in diffs):.5%}")
        if lat:
            print(f"  mean demo latency: {statistics.mean(lat):.0f} ms")
            print(f"  p95  demo latency: {_p95(lat):.0f} ms")

    print("\n=== paper vs demo aggregate ===")
    paper = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(realized_pnl),0) AS pnl "
        "FROM paper_trades WHERE exit_ts IS NOT NULL"
    ).fetchone()
    demo = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(realized_pnl),0) AS pnl "
        "FROM trades WHERE closed_at IS NOT NULL"
    ).fetchone()
    print(f"  paper: {paper['n']} trades, pnl={paper['pnl']:.5f}")
    print(f"  demo:  {demo['n']} trades, pnl={demo['pnl']:.5f}")

    # Paired comparison by prediction_id.
    pairs = conn.execute(
        """SELECT p.realized_pnl AS p, t.realized_pnl AS d
           FROM paper_trades p
           JOIN trades t ON t.prediction_id = p.prediction_id
           WHERE p.exit_ts IS NOT NULL AND t.closed_at IS NOT NULL"""
    ).fetchall()
    if pairs:
        diffs = [p["p"] - p["d"] for p in pairs if p["p"] is not None and p["d"] is not None]
        if diffs:
            print(f"\n=== paired P&L difference (n={len(diffs)}) ===")
            print(f"  mean:   {statistics.mean(diffs):+.5f}")
            print(f"  median: {statistics.median(diffs):+.5f}")
            print(f"  p95:    {_p95(diffs):+.5f}")

    return 0


def _p95(xs):
    xs = sorted(xs)
    if not xs:
        return 0.0
    i = max(0, int(0.95 * (len(xs) - 1)))
    return xs[i]


def _p95_abs(xs):
    return _p95([abs(x) for x in xs])


if __name__ == "__main__":
    sys.exit(main())