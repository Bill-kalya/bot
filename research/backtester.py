"""Backtest driver.

Usage:
    uv run python -m research.backtester --strategy momentum --days 90
    uv run python -m research.backtester --strategy all --days 90

Loads historical candles once, then replays them through the simulator for
each requested strategy. Prints a report and writes JSON to research/out/.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import UTC
from pathlib import Path

from config import Config
from core.clock import now_utc
from core.types import Candle, FeeSchedule, MarketMeta
from data.features import build_features
from research.simulator import HistoricalSimulator, SimResult
from strategy.registry import get as get_strategy

# --- candle loading ---------------------------------------------------------

def load_historical_candles(
    exchange_id: str, symbol: str, days: int, timeframe: str = "1m",
) -> list:
    """Fetch historical candles via ccxt (public endpoint, no keys needed).

    Binance enforces a per-request limit; we paginate.
    """
    from datetime import datetime

    import ccxt

    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True,
                                     "options": {"defaultType": "future"}})
    ex.load_markets()

    now_ms = int(now_utc().timestamp() * 1000)
    start_ms = now_ms - days * 86_400_000
    limit = 1500
    out = []
    cursor = start_ms
    while cursor < int(now_utc().timestamp() * 1000):
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=limit)
        if not batch:
            break
        for row in batch:
            ts = datetime.fromtimestamp(row[0] / 1000, tz=UTC)
            out.append(Candle(
                ts=ts, open=float(row[1]), high=float(row[2]),
                low=float(row[3]), close=float(row[4]), volume=float(row[5]),
            ))
        cursor = batch[-1][0] + 60_000  # next minute
    # Deduplicate, sort.
    seen = {}
    for c in out:
        seen[c.ts] = c
    return [seen[k] for k in sorted(seen)]


# --- news loading for backtest ----------------------------------------------

def load_historical_news(
    news_dir: Path,
    symbol: str,
    start_iso: str,
    end_iso: str,
) -> list:
    """Load historical news from JSONL files (one per day).

    File format: news_YYYY-MM-DD.jsonl with one NewsItem per line as JSON.
    """
    import json

    from core.clock import from_iso
    from core.types import NewsItem

    out = []
    from datetime import datetime, timedelta
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    curr = start
    while curr <= end:
        fname = news_dir / f"news_{curr.date().isoformat()}.jsonl"
        if fname.exists():
            for line in fname.read_text().splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                item = NewsItem(
                    news_id=d["news_id"],
                    source=d["source"],
                    source_item_id=d["source_item_id"],
                    url=d["url"],
                    title=d["title"],
                    body=d["body"],
                    event_time=d.get("event_time"),
                    available_time=from_iso(d["available_time"]),
                    ingested_at=from_iso(d["ingested_at"]),
                    raw_hash=d["raw_hash"],
                    scorer_version=d["scorer_version"],
                    sentiment=d["sentiment"],
                    relevance=d["relevance"],
                    event_type=d["event_type"],
                    source_reliability=d["source_reliability"],
                    superseded_by=d.get("superseded_by"),
                )
                out.append(item)
        curr += timedelta(days=1)
    return out


# --- backtest runner --------------------------------------------------------

def run_strategy(
    cfg: Config, meta, candles: list, strategy_fn, *,
    slippage_reserve: float, funding_reserve_per_8h: float,
    news_by_available: dict[str, list],
) -> SimResult:
    sim = HistoricalSimulator(
        cfg, meta,
        slippage_reserve=slippage_reserve,
        funding_reserve_per_8h=funding_reserve_per_8h,
        gap_reserve=0.001,
    )
    window_size = 60  # matches live candle_limit
    for i in range(window_size, len(candles) - 1):
        window = candles[i - window_size:i]
        decision_time = window[-1].ts
        # Filter news available at this decision time
        news = []
        for ts_iso, items in news_by_available.items():
            if ts_iso <= decision_time.isoformat():
                news.extend(items)

        def factory(_candles, window=window, news=news, decision_time=decision_time):
            feats = build_features(
                candles=window, news=news,
                decision_time=decision_time, symbol=cfg.symbol,
            )
            return strategy_fn(feats)

        sim.step(window, factory)
        sim.step_next(candles[i + 1], factory)
        if i % 5000 == 0:
            print(f"  ... {i}/{len(candles)}", file=sys.stderr)
    return sim.result


# --- metrics ----------------------------------------------------------------

def metrics(result, starting_equity: float) -> dict:
    trades = result.trades
    pnls = [t.realized_pnl or 0.0 for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)

    # Max drawdown on the equity curve.
    peak = starting_equity
    max_dd = 0.0
    for _ts, eq in result.equity_curve:
        peak = max(peak, eq)
        dd = (peak - eq) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    return {
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "total_pnl": sum(pnls),
        "mean_pnl": statistics.mean(pnls) if pnls else 0.0,
        "median_pnl": statistics.median(pnls) if pnls else 0.0,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        "starting_equity": starting_equity,
        "ending_equity": result.ending_equity,
        "return_pct": (result.ending_equity / starting_equity - 1.0)
                      if starting_equity > 0 else 0.0,
        "max_drawdown_pct": max_dd,
        "avg_fees_per_trade": statistics.mean(
            [(t.entry_fee + t.exit_fee) for t in result.trades]
        ) if result.trades else 0.0,
        "avg_funding_per_trade": statistics.mean(
            [t.funding_paid for t in result.trades]
        ) if result.trades else 0.0,
        "stop_hits": sum(1 for t in result.trades if t.close_reason == "stop"),
        "target_hits": sum(1 for t in result.trades if t.close_reason == "target"),
    }


# --- CLI --------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--strategy", default="momentum",
                   choices=["momentum", "news", "all"])
    p.add_argument("--days", type=int, default=90)
    p.add_argument("--exchange", default="binanceusdm")
    p.add_argument("--symbol", default="BTC/USDT:USDT")
    p.add_argument("--news-dir", type=Path, default=Path("research/news"),
                   help="directory with news_YYYY-MM-DD.jsonl files")
    args = p.parse_args()

    cfg = Config.from_env()

    print(f"loading {args.days} days of {args.symbol} from {args.exchange}...",
          file=sys.stderr)
    candles = load_historical_candles(args.exchange, args.symbol, args.days)
    print(f"  {len(candles)} candles", file=sys.stderr)
    if len(candles) < 200:
        print("not enough candles", file=sys.stderr)
        return 1

    # Market meta for the backtest. Fetched once at the start.
    import ccxt
    ex = getattr(ccxt, args.exchange)({"enableRateLimit": True,
                                       "options": {"defaultType": "future"}})
    ex.load_markets()
    m = ex.market(args.symbol)
    meta = MarketMeta(
        symbol=args.symbol,
        min_notional=50.0 if not m.get("limits", {}).get("cost", {}).get("min") else
                     float(m["limits"]["cost"]["min"]),
        min_quantity=float(m.get("limits", {}).get("amount", {}).get("min") or 0.001),
        quantity_step=float(m.get("precision", {}).get("amount") or 0.001),
        tick_size=float(m.get("precision", {}).get("price") or 0.1),
        max_leverage=int(m.get("limits", {}).get("leverage", {}).get("max") or 20),
        fees=FeeSchedule(
            taker=float(m.get("taker") or 0.0005),
            maker=float(m.get("maker") or 0.0002),
            fetched_at=now_utc(),
        ),
        fetched_at=now_utc(),
    )

    # Load historical news (if available)
    from datetime import timedelta
    end_iso = now_utc().isoformat()
    start_iso = (now_utc() - timedelta(days=args.days)).isoformat()
    news_by_available = {}
    try:
        loaded_news = load_historical_news(args.news_dir, args.symbol, start_iso, end_iso)
        for item in loaded_news:
            ts = item.available_time.isoformat()
            news_by_available.setdefault(ts, []).append(item)
    except (OSError, json.JSONDecodeError) as e:
        print(f"  warning: could not load news: {e}", file=sys.stderr)
        news_by_available = {}

    # Strategy registry.
    strategies = {
        "momentum": lambda f: get_strategy("momentum")(f),
        "news": lambda f: get_strategy("news")(f),
    }
    if args.strategy == "all":
        to_run = list(strategies.items())
    else:
        to_run = [(args.strategy, strategies[args.strategy])]

    out_dir = Path("research/out")
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {}
    for name, fn in to_run:
        print(f"\n=== {name} ===", file=sys.stderr)
        result = run_strategy(
            cfg, meta, candles, fn,
            slippage_reserve=cfg.slippage_reserve,
            funding_reserve_per_8h=cfg.funding_reserve,
            news_by_available=news_by_available,
        )
        m_report = metrics(result, cfg.start_equity)
        report[name] = m_report
        _print_metrics(name, m_report)

    out_path = out_dir / f"backtest_{args.strategy}_{args.days}d.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nwrote {out_path}", file=sys.stderr)
    return 0


def _print_metrics(name: str, m: dict) -> None:
    print(f"\n--- {name} ---")
    print(f"  trades:            {m['trades']}")
    print(f"  win rate:          {m['win_rate']:.1%}")
    print(f"  total P&L:         {m['total_pnl']:.4f}")
    print(f"  return:            {m['return_pct']:.2%}")
    print(f"  max drawdown:      {m['max_drawdown_pct']:.2%}")
    print(f"  profit factor:     {m['profit_factor']:.3f}")
    print(f"  avg fees/trade:    {m['avg_fees_per_trade']:.5f}")
    print(f"  avg funding/trade: {m['avg_funding_per_trade']:.5f}")
    print(f"  stop hits:         {m['stop_hits']}")
    print(f"  target hits:       {m['target_hits']}")


if __name__ == "__main__":
    import argparse
    sys.exit(main())