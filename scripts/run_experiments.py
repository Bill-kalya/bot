"""Run Phase 9 experiments.

Usage:
    python -m scripts.run_experiments --days 30 --windows 5
    python -m scripts.run_experiments --days 90 --windows 6 --accounts 10 100 1000
    python -m scripts.run_experiments --days 30 --horizons 15 60 240
"""
from __future__ import annotations

import argparse
import bisect
import logging
import sys
import time
from pathlib import Path

from config import Config
from core.clock import now_utc
from core.types import Signal
from research.experiments import run_phase9


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--windows", type=int, default=5)
    p.add_argument("--accounts", type=float, nargs="+",
                   default=[10.0, 100.0, 1000.0])
    p.add_argument("--exchange", default="binanceusdm")
    p.add_argument("--symbol", default="BTC/USDT:USDT")
    p.add_argument("--out", default=None)
    p.add_argument("--horizons", type=int, nargs="+", default=[15, 60, 240])
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    cfg = Config.from_env()

    # 1. Load candles.
    print(f"loading {args.days} days of {args.symbol}...", file=sys.stderr)
    from research.backtester import load_historical_candles
    candles = load_historical_candles(args.exchange, args.symbol, args.days)
    print(f"  {len(candles)} candles", file=sys.stderr)
    if len(candles) < args.windows * 1000:
        print("not enough candles for requested windows", file=sys.stderr)
        return 1

    # 2. Load market metadata (use fake exchange for backtesting).
    from exchange.fake_adapter import FakeExchange, default_fake_meta
    adapter = FakeExchange(default_fake_meta(args.symbol))
    adapter.load_markets()
    meta = adapter.fetch_market_meta(args.symbol)
    print(f"  meta: min_notional={meta.min_notional} max_leverage={meta.max_leverage}",
          file=sys.stderr)

    # 3. Load news (from the DB, or empty).
    from storage.db import connect, init_schema
    conn = connect(cfg.ledger_path)
    init_schema(conn)

    # Build a sorted list of (available_time_iso, NewsItem) once.
    # The lookup filters on <= decision_time.
    news_rows = conn.execute(
        "SELECT * FROM news_items WHERE superseded_by IS NULL ORDER BY available_time"
    ).fetchall()
    from storage.news import _row_to_item
    all_news = [_row_to_item(r) for r in news_rows]
    print(f"  news items: {len(all_news)}", file=sys.stderr)

    # Pre-sort news by available_time for O(log n) lookup via bisect
    all_news.sort(key=lambda n: n.available_time)
    sorted_times = [n.available_time for n in all_news]

    def news_lookup(decision_time):
        idx = bisect.bisect_right(sorted_times, decision_time)
        return all_news[:idx]

    # 4. Strategies.
    from strategy.registry import get as get_strategy
    strategies = {
        "momentum": get_strategy("momentum"),
        "news": get_strategy("news"),
    }
    if cfg.regime_filter_enabled:
        strategies["news_filtered"] = get_strategy("news_filtered")
    # Add baselines.
    def random_wrapper(feats):
        # Random baseline needs candles, not features. In Experiment 1 we
        # have features only. Emit a deterministic pseudo-random signal.
        import hashlib
        seed = hashlib.sha256(
            f"{feats.decision_time.isoformat()}::{feats.price}".encode()
        ).digest()
        coin = seed[0] / 255.0
        direction = 1 if coin < 0.5 else -1
        return Signal(
            decision_time=feats.decision_time, symbol=feats.symbol,
            horizon_minutes=15, direction=direction, confidence=0.5,
            expected_signed_return=0.005 * direction,
            expected_volatility=max(0.001, feats.volatility_15m),
            source_version="random-v0.2.0",
        )
    strategies["random"] = random_wrapper

    # 5. Output dir.
    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) if args.out else Path(f"research/out/phase9_{ts}")

    # 6. Run.
    t0 = time.monotonic()
    run_phase9(
        cfg, meta, candles, news_lookup, strategies,
        n_windows=args.windows,
        account_sizes=args.accounts,
        horizons=tuple(args.horizons),
        out_dir=out_dir,
    )
    elapsed = time.monotonic() - t0

    print(f"\nwrote {out_dir}/summary.json", file=sys.stderr)
    print(f"wrote {out_dir}/summary.md", file=sys.stderr)
    print(f"elapsed: {elapsed:.1f}s", file=sys.stderr)

    # Print the markdown to stdout.
    print((out_dir / "summary.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())