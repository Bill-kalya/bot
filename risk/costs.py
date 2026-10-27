"""Per-trade cost model.

All reserves are policy (from Config), not market facts. Actual fees come
from MarketMeta, which itself came from the exchange at runtime.

A trade's expected net return is:
    direction * expected_signed_return
    - entry_fee - exit_fee
    - slippage_reserve
    - funding_reserve
    - latency_reserve
"""
from __future__ import annotations

from dataclasses import dataclass

from config import Config
from core.types import MarketMeta, Signal


@dataclass(frozen=True)
class CostBreakdown:
    entry_fee: float
    exit_fee: float
    slippage: float
    funding: float
    latency: float
    total: float


def estimate_costs(signal: Signal, market: MarketMeta, cfg: Config) -> CostBreakdown:
    entry_fee = market.fees.taker
    exit_fee = market.fees.taker
    # Slippage scales with forecast volatility; a calm market slips less.
    slippage = cfg.slippage_reserve * (1.0 + signal.expected_volatility / 0.01)
    funding = cfg.funding_reserve
    latency = cfg.latency_reserve
    total = entry_fee + exit_fee + slippage + funding + latency
    return CostBreakdown(entry_fee, exit_fee, slippage, funding, latency, total)


def expected_net_trade_return(
    signal: Signal, market: MarketMeta, cfg: Config
) -> tuple[float, CostBreakdown]:
    """Return (expected_net_return, cost_breakdown).

    The net return is directional: for a short, a negative
    expected_signed_return produces a positive gross trade return.
    """
    costs = estimate_costs(signal, market, cfg)
    gross = signal.direction * signal.expected_signed_return
    return gross - costs.total, costs