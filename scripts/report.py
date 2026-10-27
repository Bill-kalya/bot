"""Print a summary report from the ledger DB.

Usage:
    uv run python scripts/report.py

Sections:
  - Prediction counts and approval rate
  - Net return by confidence bucket (the calibration check)
  - Trade P&L summary
  - Cost breakdown

Everything is net of estimated costs. No cherry-picking, no filtering to
"interesting" periods.
"""
from __future__ import annotations

import statistics
import sys
from collections import defaultdict

from config import Config
from storage.db import connect


def main() -> int:
    cfg = Config.from_env()
    if not cfg.ledger_path.exists():
        print(f"no ledger at {cfg.ledger_path}", file=sys.stderr)
        return 1

    conn = connect(cfg.ledger_path)

    _predictions_summary(conn)
    _calibration_table(conn)
    _trades_summary(conn)

    return 0


def _predictions_summary(conn) -> None:
    total = conn.execute("SELECT COUNT(*) AS n FROM predictions").fetchone()["n"]
    approved = conn.execute(
        "SELECT COUNT(*) AS n FROM predictions WHERE risk_decision='APPROVED'"
    ).fetchone()["n"]
    labeled = conn.execute("SELECT COUNT(*) AS n FROM outcomes").fetchone()["n"]

    print("=== predictions ===")
    print(f"total:       {total}")
    print(f"approved:    {approved} ({approved / total:.1%})" if total else "approved:    0")
    print(f"labeled:     {labeled} ({labeled / total:.1%})" if total else "labeled:     0")

    print("\ntop rejection reasons:")
    rows = conn.execute(
        """SELECT rejection_reason, COUNT(*) AS n
           FROM predictions
           WHERE risk_decision='REJECTED'
           GROUP BY rejection_reason
           ORDER BY n DESC LIMIT 10"""
    ).fetchall()
    for r in rows:
        print(f"  {r['n']:>6}  {r['rejection_reason']}")


def _calibration_table(conn) -> None:
    """Confidence bucket vs average net return. This is the money table.

    If higher confidence does not correspond to higher average net return,
    the confidence score is not informative and the model has no edge.
    """
    rows = conn.execute(
        """SELECT p.confidence, o.net_return_15m
           FROM predictions p
           JOIN outcomes o ON o.prediction_id = p.prediction_id
           WHERE p.direction != 0
             AND o.net_return_15m IS NOT NULL"""
    ).fetchall()

    buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        c = float(r["confidence"])
        if c < 0.2:
            key = "[0.0, 0.2)"
        elif c < 0.4:
            key = "[0.2, 0.4)"
        elif c < 0.6:
            key = "[0.4, 0.6)"
        elif c < 0.8:
            key = "[0.6, 0.8)"
        else:
            key = "[0.8, 1.0]"
        buckets[key].append(float(r["net_return_15m"]))

    print("\n=== calibration: confidence vs net 15m return ===")
    if not buckets:
        print("  no labeled directional predictions yet")
        return
    print(f"  {'bucket':<12} {'n':>6} {'mean_net':>10} {'median_net':>12} {'hit_rate':>10}")
    for key in sorted(buckets.keys()):
        vals = buckets[key]
        mean = statistics.mean(vals)
        median = statistics.median(vals)
        hit = sum(1 for v in vals if v > 0) / len(vals)
        print(f"  {key:<12} {len(vals):>6} {mean:>10.5f} {median:>12.5f} {hit:>10.1%}")


def _trades_summary(conn) -> None:
    rows = conn.execute(
        """SELECT side, realized_pnl, fees_paid, funding_paid
           FROM trades WHERE closed_at IS NOT NULL"""
    ).fetchall()
    print("\n=== trades ===")
    if not rows:
        print("  none closed yet")
        return
    pnls = [float(r["realized_pnl"] or 0.0) for r in rows]
    fees = sum(float(r["fees_paid"] or 0.0) for r in rows)
    funding = sum(float(r["funding_paid"] or 0.0) for r in rows)
    print(f"  closed:       {len(rows)}")
    print(f"  total P&L:    {sum(pnls):.5f}")
    print(f"  fees paid:    {fees:.5f}")
    print(f"  funding paid: {funding:.5f}")
    print(f"  wins:         {sum(1 for p in pnls if p > 0)}")
    print(f"  losses:       {sum(1 for p in pnls if p < 0)}")


if __name__ == "__main__":
    sys.exit(main())