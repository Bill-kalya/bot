"""Account-size sweep.

Runs the full pipeline (features -> strategy -> risk -> simulator) at
multiple starting equities. The point is to see where the cost structure
stops being the binding constraint.

At $10 with a $50 minimum notional, cost drag is ~1% of equity per round trip.
At $1000, it is ~0.01%. The sweep shows the shape of the transition.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

from config import Config
from core.types import Candle, MarketMeta
from research.simulator import HistoricalSimulator

log = logging.getLogger(__name__)


@dataclass
class SweepResult:
    starting_equity: float
    ending_equity: float
    n_trades: int
    n_wins: int
    n_losses: int
    total_pnl: float
    total_fees: float
    total_funding: float
    max_drawdown_pct: float


def run_sweep(
    base_cfg: Config,
    meta: MarketMeta,
    candles: list[Candle],
    news_at,
    strategy_fn,
    build_features_fn,
    account_sizes: list[float],
    *,
    window_size: int = 60,
) -> list[SweepResult]:
    results: list[SweepResult] = []
    for equity in account_sizes:
        # Clone config with a different starting equity.
        cfg = Config(**{**base_cfg.__dict__, "start_equity": equity})
        result = _run_one(cfg, meta, candles, news_at, strategy_fn,
                          build_features_fn, window_size)
        results.append(result)
    return results


def _run_one(cfg, meta, candles, news_at, strategy_fn, build_features_fn,
             window_size) -> SweepResult:
    sim = HistoricalSimulator(
        cfg, meta,
        slippage_reserve=cfg.slippage_reserve,
        funding_reserve_per_8h=cfg.funding_reserve,
        gap_reserve=0.001,
    )

    total = len(candles) - window_size - 1
    for i in range(window_size, len(candles) - 1):
        if i % 1000 == 0:
            print(f"        [sweep] progress: {i}/{total} candles", file=sys.stderr)
        window = candles[i - window_size:i]
        decision_time = window[-1].ts
        news = news_at(decision_time)

        def factory(_candles, w=window, n=news, dt=decision_time):
            feats = build_features_fn(w, n, dt, cfg.symbol)
            return strategy_fn(feats)

        sim.step(window, factory)
        sim.step_next(candles[i + 1], factory)

    trades = sim.result.trades
    pnls = [t.realized_pnl or 0.0 for t in trades]
    fees = sum(t.entry_fee + t.exit_fee for t in trades)
    funding = sum(t.funding_paid for t in trades)

    peak = cfg.start_equity
    max_dd = 0.0
    for _ts, eq in sim.result.equity_curve:
        peak = max(peak, eq)
        dd = (peak - eq) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

    return SweepResult(
        starting_equity=cfg.start_equity,
        ending_equity=sim.equity,
        n_trades=len(trades),
        n_wins=sum(1 for p in pnls if p > 0),
        n_losses=sum(1 for p in pnls if p < 0),
        total_pnl=sum(pnls),
        total_fees=fees,
        total_funding=funding,
        max_drawdown_pct=max_dd,
    )