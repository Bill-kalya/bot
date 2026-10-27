"""Risk engine entry point.

    decision = evaluate(signal, account, market, price, cfg)

Returns Approve(plan) or RejectDecision(reason). Never raises for policy
reasons. Every rejection has a distinct, human-readable reason that lands in
the predictions table.

Design invariants:
  - No exchange calls. No I/O. No logging side-effects.
  - The strategy cannot bypass this by any code path.
  - A reject is not an error. It is a normal outcome and is logged.
"""
from __future__ import annotations

import logging

from config import Config
from core.types import (
    Approve,
    Decision,
    MarketMeta,
    RejectDecision,
    Signal,
)
from risk.account import Account
from risk.costs import CostBreakdown, expected_net_trade_return
from risk.limits import (
    check_concurrency,
    check_confidence,
    check_daily_cap,
    check_kill_switch,
    check_liquidation_buffer,
    check_net_edge,
    check_worst_case_loss,
)
from risk.sizing import plan_position

log = logging.getLogger(__name__)


def evaluate(
    signal: Signal,
    account: Account,
    market: MarketMeta,
    price: float,
    cfg: Config,
) -> tuple[Decision, CostBreakdown]:
    """Return (decision, cost_breakdown). Costs are returned even on reject
    so the prediction log can record what the trade *would* have cost."""
    net_return, costs = expected_net_trade_return(signal, market, cfg)

    # Diagnostic: log the full cost breakdown (only when explicitly enabled)
    if getattr(cfg, "log_risk_evaluations", False):
        gross = signal.direction * signal.expected_signed_return
        log.info(
            "risk: gross=%.6f entry_fee=%.6f exit_fee=%.6f slippage=%.6f funding=%.6f latency=%.6f total_cost=%.6f net=%.6f",
            gross,
            costs.entry_fee,
            costs.exit_fee,
            costs.slippage,
        costs.funding,
        costs.latency,
        costs.total,
        net_return,
    )

    # 1. Categorical halts — nothing overrides these.
    for reason in (
        check_kill_switch(cfg),
        check_daily_cap(account, cfg),
        check_concurrency(account),
    ):
        if reason:
            return RejectDecision(reason), costs

    # 2. Direction must be non-zero to proceed past signal checks.
    if signal.direction == 0:
        return RejectDecision("hold signal"), costs

    # 3. Signal quality.
    for reason in (
        check_confidence(signal.confidence, cfg),
        check_net_edge(net_return, cfg),
    ):
        if reason:
            return RejectDecision(reason), costs

    # 4. Position sizing against real exchange constraints.
    plan = plan_position(signal, account.equity, market, price, cfg)
    if isinstance(plan, RejectDecision):
        return plan, costs

    approved = Approve(plan)

    # 5. Plan-level safety.
    for reason in (
        check_worst_case_loss(approved, account, cfg),
        check_liquidation_buffer(approved, account, cfg),
    ):
        if reason:
            return RejectDecision(reason), costs

    return approved, costs