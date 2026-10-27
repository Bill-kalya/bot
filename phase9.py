"""Phase 9 entrypoint — Signal Quality & Net Economics.

Two experiments:
  1. Signal quality: Does the signal predict future returns? (Ignores costs)
  2. Net economics: Can the signal produce profit at $10/$100/$1000?
"""
from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any

from config import Config
from core.clock import now_utc
from core.types import Approve, Candle
from data.features import build_features
from exchange.fake_adapter import FakeExchange, default_fake_meta
from research.metrics import (
    SignalMetrics,
    bootstrap_metrics,
    compute_signal_metrics,
    print_signal_metrics,
)
from research.signal_study import run_signal_study
from storage.db import connect, init_schema
from strategy.registry import get as get_strategy

log = logging.getLogger(__name__)


STRATEGIES = ["momentum", "news"]
ACCOUNT_SIZES = [10.0, 100.0, 1000.0]


def _build_fake_exchange():
    """Build a fake exchange with realistic market data for backtesting."""
    meta = default_fake_meta("BTC/USDT:USDT")
    ex = FakeExchange(meta)
    ex.load_markets()
    return ex


def _generate_synthetic_candles(n: int, start_price: float = 85000.0) -> list[Candle]:
    """Generate synthetic candles with slight random walk for testing."""
    candles = []
    price = start_price
    base_time = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    base_time = base_time - timedelta(minutes=n)

    for i in range(n):
        # Small random walk with slight mean reversion
        change = random.gauss(0, 0.0005)  # 5 bps per minute
        price = price * (1 + change)
        # Mean revert slightly
        price = price * 0.9999 + start_price * 0.0001

        ts = base_time + timedelta(minutes=i)
        candles.append(Candle(
            ts=ts,
            open=price,
            high=price * (1 + abs(random.gauss(0, 0.0002))),
            low=price * (1 - abs(random.gauss(0, 0.0002))),
            close=price,
            volume=random.uniform(10, 1000),
        ))

    return candles


def _collect_news_by_time(cfg: Config, hours: int = 24) -> dict[str, list]:
    """Collect news items grouped by available time for the study period."""
    from data.news.pipeline import ingest
    from data.news.rss_collector import RSSCollector

    conn = connect(cfg.ledger_path)
    init_schema(conn)

    end_time = now_utc()
    start_time = end_time - timedelta(hours=hours)

    collectors = [
        RSSCollector(name, url, source_reliability=rel)
        for (name, url, rel) in cfg.news_feeds
    ]

    news_by_time: dict[str, list] = {}

    current = start_time
    while current <= end_time:
        current_iso = current.isoformat()
        for c in collectors:
            try:
                result = ingest(conn, c)
                if result.get("items"):
                    if current_iso not in news_by_time:
                        news_by_time[current_iso] = []
                    news_by_time[current_iso].extend(result.get("items", []))
            except Exception as e:  # noqa: BLE001
                log.warning("news collection failed: %s", e)
        current += timedelta(seconds=cfg.news_poll_seconds)

    return news_by_time


def run_experiment_1_signal_quality(cfg: Config) -> dict[str, SignalMetrics]:
    """Experiment 1: Signal quality study.

    Runs all strategies through historical data and computes:
    - Hit rate at 15m/60m
    - Mean signed return
    - Confidence calibration
    - Bootstrap confidence intervals

    Returns:
        Dict mapping strategy name to SignalMetrics.
    """
    print(f"\n{'='*70}")
    print("EXPERIMENT 1: SIGNAL QUALITY STUDY")
    print(f"{'='*70}")

    # Use fake exchange for consistent testing
    _build_fake_exchange()

    # Generate synthetic candles (or use real ones if available)
    candles = _generate_synthetic_candles(24 * 60)  # 24 hours of 1m candles

    # Collect news
    news_by_time = _collect_news_by_time(cfg, hours=24)

    results = {}

    for strat_name in STRATEGIES:
        print(f"\nRunning signal study for: {strat_name}")

        signals = run_signal_study(
            candles=candles,
            news_by_available=news_by_time,
            strategy_name=strat_name,
            symbol=cfg.symbol,
            model_version=cfg.model_version,
            feature_version=cfg.feature_version,
            config_version=cfg.config_version,
        )

        if not signals:
            print(f"  No signals generated for {strat_name}")
            results[strat_name] = SignalMetrics(
                n=0, hit_rate_15m=0.0, hit_rate_60m=0.0,
                mean_signed_return_15m=0.0, mean_signed_return_60m=0.0,
                confidence_buckets={}
            )
            continue

        metrics = compute_signal_metrics(signals)
        bootstrap = bootstrap_metrics(signals)

        print_signal_metrics(metrics, bootstrap, name=strat_name)

        results[strat_name] = metrics

    return results


def run_experiment_2_net_economics(cfg: Config) -> dict[float, dict[str, Any]]:
    """Experiment 2: Net economics at multiple account sizes.

    Runs the full pipeline (strategy -> risk -> simulator) at different
    equity levels and compares results.

    Returns:
        Dict mapping equity size to results dict.
    """
    print(f"\n{'='*70}")
    print("EXPERIMENT 2: NET ECONOMICS AT MULTIPLE ACCOUNT SIZES")
    print(f"{'='*70}")

    from execution.paper import PaperExecutor
    from risk.account import Account
    from risk.engine import evaluate

    ex = _build_fake_exchange()
    ex.load_markets()
    meta = ex.fetch_market_meta(cfg.symbol)

    # Generate candles for the study period
    candles = _generate_synthetic_candles(48 * 60)  # 48 hours
    news_by_time = _collect_news_by_time(cfg, hours=48)

    results = {}

    for equity in ACCOUNT_SIZES:
        print(f"\n--- Account size: ${equity:.0f} ---")

        # Create paper executor for this equity
        conn = connect(cfg.ledger_path)
        init_schema(conn)

        paper = PaperExecutor(
            cfg, meta, ex, conn,
            equity=equity,
            slippage_reserve=cfg.slippage_reserve,
            funding_reserve_per_8h=cfg.funding_reserve,
            gap_reserve=0.001,
        )

        strategy_fn = get_strategy(cfg.strategy_name)

        trades = []
        equity_curve = [equity]

        for i in range(60, len(candles) - 61):
            window = candles[i - 60:i]
            decision_time = window[-1].ts

            # Get news
            decision_iso = decision_time.isoformat()
            recent_news = []
            for ts, items in news_by_time.items():
                if ts <= decision_iso:
                    recent_news.extend(items)

            # Build features
            try:
                features = build_features(
                    candles=window,
                    news=recent_news,
                    decision_time=decision_time,
                    symbol=cfg.symbol,
                )
            except ValueError:
                continue

            signal = strategy_fn(features)
            if signal.direction == 0:
                continue

            # Risk evaluation
            account = Account(
                equity=paper.equity,
                daily_baseline=paper.daily_baseline,
                peak_equity=paper.peak_equity,
                open_positions=0,
            )
            decision, _costs = evaluate(signal, account, meta, window[-1].close, cfg)

            if isinstance(decision, Approve):
                # Paper trade
                paper.open_position(decision, f"study-{i}", meta=meta)
                position = paper.get_position()

                # Track entry
                entry_price = position.entry_price
                entry_equity = paper.equity

                # Simulate holding for 15 minutes (or until exit)
                max_hold = 15
                for hold_idx in range(1, max_hold + 1):
                    if i + hold_idx >= len(candles):
                        break
                    price = candles[i + hold_idx].close
                    paper.tick(price)

                    # Check if stop/target hit
                    if position is None:
                        break

                # Close position
                exit_equity = paper.equity
                pnl = exit_equity - entry_equity
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pnl": pnl,
                    "pnl_pct": pnl / entry_equity,
                })
                equity_curve.append(paper.equity)

        total_pnl = sum(t["pnl"] for t in trades)
        total_pnl_pct = total_pnl / equity if equity > 0 else 0
        avg_pnl = total_pnl / len(trades) if trades else 0

        results[equity] = {
            "equity": equity,
            "trades": len(trades),
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "avg_pnl_per_trade": avg_pnl,
            "equity_curve": equity_curve,
        }

        print(f"  Trades: {len(trades)}")
        print(f"  Total P&L: ${total_pnl:.4f} ({total_pnl_pct:.2%})")
        print(f"  Avg P&L/trade: ${avg_pnl:.4f}")

    return results


def run_phase9():
    """Run both Phase 9 experiments."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    cfg = Config.from_env()
    cfg.state_dir.mkdir(parents=True, exist_ok=True)

    # Experiment 1: Signal Quality
    signal_results = run_experiment_1_signal_quality(cfg)

    # Experiment 2: Net Economics
    economics_results = run_experiment_2_net_economics(cfg)

    # Summary
    print(f"\n{'='*70}")
    print("PHASE 9 SUMMARY")
    print(f"{'='*70}")

    print("\nExperiment 1 (Signal Quality):")
    for name, metrics in signal_results.items():
        if metrics.n > 0:
            print(f"  {name}: n={metrics.n}, hit_15m={metrics.hit_rate_15m:.2%}, "
                  f"mean_ret_15m={metrics.mean_signed_return_15m:.6f}")

    print("\nExperiment 2 (Net Economics):")
    for equity, res in economics_results.items():
        print(f"  ${equity:.0f}: trades={res['trades']}, "
              f"P&L=${res['total_pnl']:.4f} ({res['total_pnl_pct']:.2%})")


if __name__ == "__main__":
    run_phase9()