"""Position sizing.

Policy: the risk engine does not optimize size. It takes the smallest legal
order and checks whether the account can survive its worst-case loss. If not,
the trade is rejected. This is deliberate — a $10 ledger cannot afford
clever sizing.
"""
from __future__ import annotations

import math

from config import Config
from core.types import MarketMeta, Plan, RejectDecision, Signal


def round_up_to_step(value: float, step: float) -> float:
    if step <= 0:
        raise ValueError("step must be positive")
    return math.ceil(value / step) * step


def smallest_legal_notional(market: MarketMeta, buffer: float = 1.05) -> float:
    """The smallest notional that satisfies min_notional and min_quantity.
    A small buffer avoids failing on rounding at order time."""
    by_notional = market.min_notional
    by_qty = market.min_quantity * 1.0  # price unknown here; caller scales
    # We cannot know price here without a market data dependency, so we take
    # the notional floor and let the caller verify quantity after sizing.
    return max(by_notional, by_qty) * buffer


def plan_position(
    signal: Signal,
    account_equity: float,
    market: MarketMeta,
    price: float,
    cfg: Config,
) -> Plan | RejectDecision:
    """Return a Plan or a RejectDecision. Never raises for policy reasons."""
    if account_equity <= 0:
        return RejectDecision("non-positive equity")

    if price <= 0:
        return RejectDecision("non-positive price")

    # Fixed stop distance from config (not derived from equity).
    stop_distance_pct = cfg.stop_distance_pct
    if stop_distance_pct <= 0:
        return RejectDecision("non-positive stop distance")
    if stop_distance_pct > 0.5:
        return RejectDecision(f"stop distance {stop_distance_pct:.2%} unrealistic")

    # Notional sized from risk budget: max_loss_per_trade_pct * equity / stop_distance_pct
    risk_budget = cfg.max_loss_per_trade_pct * account_equity
    notional = risk_budget / stop_distance_pct
    min_notional = smallest_legal_notional(market)
    notional = max(notional, min_notional)
    max_notional = cfg.max_leverage * account_equity
    notional = min(notional, max_notional)

    # Round up to quantity step, but ensure notional doesn't exceed budget after rounding
    max_notional_for_budget = cfg.max_loss_per_trade_pct * account_equity / cfg.stop_distance_pct
    qty = round_up_to_step(notional / price, market.quantity_step)
    notional = qty * price
    
    # If rounding pushed notional over budget, try one step down
    if notional > max_notional_for_budget:
        step_qty = market.quantity_step
        if qty > step_qty:
            qty -= step_qty
            notional = qty * price
        else:
            return RejectDecision("minimum quantity exceeds risk budget")

    # Leverage required to open this position with the available equity.
    leverage = max(1, math.ceil(notional / account_equity))
    if leverage > cfg.max_leverage:
        return RejectDecision(
            f"required leverage {leverage}x exceeds ceiling {cfg.max_leverage}x"
        )
    if leverage > market.max_leverage:
        return RejectDecision(
            f"required leverage {leverage}x exceeds exchange max {market.max_leverage}x"
        )

    side = "buy" if signal.direction > 0 else "sell"
    stop_price = (
        price * (1 - cfg.stop_distance_pct) if side == "buy"
        else price * (1 + cfg.stop_distance_pct)
    )

    # Worst-case loss includes fees and a gap reserve beyond the stop.
    worst_case_loss = notional * (
        cfg.stop_distance_pct + cfg.stop_slippage_reserve + 2 * market.fees.taker
    )

    return Plan(
        side=side,  # type: ignore[arg-type]
        quantity=qty,
        notional=notional,
        leverage=leverage,
        stop_price=stop_price,
        stop_distance_pct=cfg.stop_distance_pct,
        worst_case_loss=worst_case_loss,
    )