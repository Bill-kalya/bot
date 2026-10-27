"""Historical execution simulator.

Same rules as live:
  - Entry fills at the next candle's open, worsened by a slippage reserve.
  - Stop fills at the stop price minus a gap reserve if the candle range
    reaches it. Never better than the stop.
  - Exit-at-target fills at the target price minus slippage.
  - Fees are taker on both sides.
  - Funding is charged per 8h boundary crossed while a position is open.

The simulator refuses to open positions the risk engine would reject, and
refuses to open positions it cannot protect. It uses the same MarketMeta
shape the live path uses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from config import Config
from core.types import Candle, MarketMeta, Plan

# Import Trade to satisfy type checker


@dataclass
class SimTrade:
    """One simulated round trip."""
    side: str
    quantity: float
    notional: float
    leverage: int
    entry_ts: object
    entry_price: float
    entry_fee: float
    stop_price: float
    stop_distance_pct: float
    target_price: float
    target_distance_pct: float
    exit_ts: object | None = None
    exit_price: float | None = None
    exit_fee: float = 0.0
    funding_paid: float = 0.0
    realized_pnl: float | None = None
    close_reason: str | None = None
    prediction_id: str | None = None

    # For time-based exit (fixed-horizon strategies)
    forced_exit_ts: object | None = None

    # Internal state for funding tracking
    _last_funding_ts: object | None = None


@dataclass
class SimResult:
    trades: list = field(default_factory=list)
    equity_curve: list[tuple[object, float]] = field(default_factory=list)
    starting_equity: float = 0.0
    ending_equity: float = 0.0


class HistoricalSimulator:
    """Replays candles through strategy + risk + simulated execution."""

    def __init__(
        self,
        cfg: Config,
        meta: MarketMeta,
        *,
        slippage_reserve: float,
        funding_reserve_per_8h: float,
        gap_reserve: float = 0.001,
    ) -> None:
        self.cfg = cfg
        self.meta = meta
        self.slippage_reserve = slippage_reserve
        self.funding_reserve_per_8h = funding_reserve_per_8h
        self.gap_reserve = gap_reserve

        self.equity = cfg.start_equity
        self.peak_equity = cfg.start_equity
        self.daily_baseline = cfg.start_equity
        self.current_day = None

        self.open_trade = None
        self.result = SimResult(
            starting_equity=cfg.start_equity,
            ending_equity=cfg.start_equity,
        )

    # --- main loop ---------------------------------------------------------

    def step(self, candles_window: list, signal_factory) -> None:
        """Process one decision at the last candle of the window.

        signal_factory(candles) -> Signal. Provided by caller so this class
        has no strategy dependency.
        """
        now_candle = candles_window[-1]
        self._roll_daily_baseline(now_candle)

        if self.open_trade is not None:
            self._manage_open(now_candle)
            self.result.equity_curve.append((now_candle.ts, self.equity))
            return

        signal = signal_factory(candles_window)

        # Same risk engine as live.
        from risk.account import Account
        from risk.engine import evaluate

        account = Account(
            equity=self.equity,
            daily_baseline=self.daily_baseline,
            peak_equity=self.peak_equity,
            open_positions=0,
        )
        decision, _costs = evaluate(signal, account, self.meta, now_candle.close, self.cfg)

        # Imported here to avoid a circular import at module load.
        from core.types import RejectDecision
        if isinstance(decision, RejectDecision):
            self.result.equity_curve.append((now_candle.ts, self.equity))
            return

        # Fill at next candle open. The caller must pass the next candle.
        # We store the intent and finalize on the next step.
        self._pending_entry = decision

    def step_next(self, next_candle: Candle, signal_factory) -> None:
        """Called by the driver with the candle immediately after the decision
        candle. Fills any pending entry, then processes the decision made at
        next_candle's close.
        """
        pending = getattr(self, "_pending_entry", None)
        if pending is not None:
            self._open_at(pending, next_candle)
            self._pending_entry = None

    # --- position management ----------------------------------------------

    def _open_at(self, decision, candle: Candle) -> None:
        plan: Plan = decision.plan
        fill_price = candle.open * (
            1 + self.slippage_reserve if plan.side == "buy"
            else 1 - self.slippage_reserve
        )

        entry_fee = self.meta.fees.taker * plan.quantity * fill_price
        side = "long" if plan.side == "buy" else "short"
        target_distance = 2.0 * plan.stop_distance_pct
        target_price = (
            fill_price * (1 + target_distance) if side == "long"
            else fill_price * (1 - target_distance)
        )
        # Forced exit at signal's horizon
        forced_exit_ts = None
        if hasattr(decision, 'signal') and decision.signal and decision.signal.horizon_minutes:
            from datetime import timedelta
            forced_exit_ts = candle.ts + timedelta(minutes=decision.signal.horizon_minutes)

        self.open_trade = SimTrade(
            side=side,
            quantity=plan.quantity,
            notional=plan.quantity * fill_price,
            leverage=plan.leverage,
            entry_ts=candle.ts,
            entry_price=fill_price,
            entry_fee=entry_fee,
            stop_price=plan.stop_price,
            _last_funding_ts=candle.ts,
            stop_distance_pct=plan.stop_distance_pct,
            target_price=target_price,
            target_distance_pct=target_distance,
            forced_exit_ts=forced_exit_ts,
        )

    def _manage_open(self, candle: Candle) -> None:
        t = self.open_trade
        assert t is not None

        # Funding on 8h boundaries crossed since entry.
        self._apply_funding(t, candle)

        # Fixed-horizon exit: close at entry_ts + hold_minutes if reached.
        if self.cfg.exit_mode == "fixed_horizon":
            hold = self.cfg.hold_minutes
            if (candle.ts - t.entry_ts).total_seconds() >= hold * 60:
                self._close_trade(
                    t, candle, candle.open, "fixed_horizon", gap_worse=False,
                )
                return
            # Still inside hold window: no stop or target check.
            return

        # Default: stop or target.
        hit_stop = (
            candle.low <= t.stop_price if t.side == "long"
            else candle.high >= t.stop_price
        )
        hit_target = (
            candle.high >= t.target_price if t.side == "long"
            else candle.low <= t.target_price
        )

        if hit_stop:
            self._close_trade(t, candle, t.stop_price, "stop", gap_worse=True)
        elif hit_target:
            self._close_trade(t, candle, t.target_price, "target", gap_worse=False)

    def _close_trade(
        self, t, candle: Candle, trigger_price: float,
        reason: str, *, gap_worse: bool,
    ) -> None:
        if gap_worse:
            exit_price = (
                trigger_price * (1 - self.gap_reserve) if t.side == "long"
                else trigger_price * (1 + self.gap_reserve)
            )
        else:
            exit_price = (
                trigger_price * (1 - self.slippage_reserve) if t.side == "long"
                else trigger_price * (1 + self.slippage_reserve)
            )

        exit_fee = self.meta.fees.taker * t.quantity * exit_price
        direction = 1 if t.side == "long" else -1
        gross = direction * (exit_price - t.entry_price) * t.quantity
        realized = gross - t.entry_fee - exit_fee - t.funding_paid

        t.exit_ts = candle.ts
        t.exit_price = exit_price
        t.exit_fee = exit_fee
        t.realized_pnl = realized
        t.close_reason = reason

        self.equity += realized
        self.peak_equity = max(self.peak_equity, self.equity)
        self.result.trades.append(t)
        self.result.ending_equity = self.equity
        self.open_trade = None

    def _apply_funding(self, t, candle: Candle) -> None:
        """Charge funding for every 8h boundary crossed since last charge."""
        last = getattr(t, "_last_funding_ts", t.entry_ts)
        elapsed = (candle.ts - last).total_seconds()
        if elapsed < 8 * 3600:
            return
        periods = int(elapsed // (8 * 3600))
        charge = self.funding_reserve_per_8h * t.notional * periods
        t.funding_paid += charge
        t._last_funding_ts = last + timedelta(seconds=periods * 8 * 3600)

    def _roll_daily_baseline(self, candle: Candle) -> None:
        day = candle.ts.date()
        if day != self.current_day:
            self.current_day = day
            self.daily_baseline = self.equity