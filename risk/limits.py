"""Hard limits. Each returns a RejectDecision reason or None.

These are independent of the model and cannot be overridden by signal
confidence or expected return.
"""
from __future__ import annotations

from config import Config
from core.types import Approve, Plan
from risk.account import Account


def check_kill_switch(cfg: Config) -> str | None:
    return "kill switch active" if cfg.kill_switch_active() else None


def check_daily_cap(account: Account, cfg: Config) -> str | None:
    if account.daily_loss_pct >= cfg.daily_loss_cap_pct:
        return (
            f"daily loss {account.daily_loss_pct:.2%} "
            f">= cap {cfg.daily_loss_cap_pct:.2%}"
        )
    return None


def check_concurrency(account: Account) -> str | None:
    if account.open_positions > 0:
        return "position already open; one at a time"
    return None


def check_confidence(signal_confidence: float, cfg: Config) -> str | None:
    if signal_confidence < cfg.min_confidence:
        return (
            f"confidence {signal_confidence:.2f} < min {cfg.min_confidence:.2f}"
        )
    return None


def check_net_edge(net_return: float, cfg: Config) -> str | None:
    if net_return <= cfg.min_edge:
        return (
            f"expected net return {net_return:.5f} <= min edge {cfg.min_edge:.5f}"
        )
    return None


def check_worst_case_loss(
    approved: Approve, account: Account, cfg: Config
) -> str | None:
    """Check that the stop loss itself doesn't exceed the per-trade budget.
    The worst_case_loss includes fees and gap reserve; we compare only the
    stop component against the budget since fees are unavoidable."""
    budget = account.equity * cfg.max_loss_per_trade_pct
    stop_loss = approved.plan.notional * approved.plan.stop_distance_pct
    if stop_loss > budget:
        return (
            f"stop loss {stop_loss:.4f} exceeds per-trade budget {budget:.4f}"
        )
    return None


def check_liquidation_buffer(
    approved: Approve, account: Account, cfg: Config
) -> str | None:
    """A rough check: if the stop is wider than the distance to liquidation at
    the planned leverage, reject. Exact liquidation price comes from the
    exchange in Phase 3 and will replace this estimate."""
    plan: Plan = approved.plan
    if plan.leverage <= 0:
        return "non-positive leverage"
    # Approximate distance to liquidation at isolated margin, ignoring fees.
    approx_liq_distance_pct = 1.0 / plan.leverage
    # Require the stop to sit at least 25% inside the liquidation distance.
    if plan.stop_distance_pct > 0.75 * approx_liq_distance_pct:
        return (
            f"stop {plan.stop_distance_pct:.2%} too close to "
            f"liquidation {approx_liq_distance_pct:.2%}"
        )
    return None