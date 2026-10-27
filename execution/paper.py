"""Paper execution.

Fills against real market ticks, not synthetic candles. Same rules the
historical simulator uses:
  - entry fills at the mid price (from ticker) worsened by a slippage reserve
  - stop fills at the stop price worsened by a gap reserve
  - exit-at-target fills at the target worsened by slippage
  - taker fees on both sides
  - funding charged on 8h boundaries crossed

Runs in a background thread. Never sends orders. Every fill is written to
the paper_trades table and to the events log.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import timedelta

from config import Config
from core.clock import now_utc, to_iso
from core.types import MarketMeta
from exchange.adapter import Exchange
from storage.logger import log_event

log = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    side: str
    quantity: float
    entry_price: float
    entry_ts: object
    stop_price: float
    stop_distance_pct: float
    target_price: float
    target_distance_pct: float
    entry_fee: float
    funding_paid: float
    prediction_id: str
    trade_id: str
    last_funding_ts: object


class PaperExecutor:
    """Executes approved decisions against live price only.

    Usage:
        paper = PaperExecutor(cfg, meta, ex, conn, ledger_equity=10.0)
        paper.submit_entry(decision, prediction_id)
        paper.tick()  # called periodically from the main loop
    """

    def __init__(
        self,
        cfg: Config,
        meta: MarketMeta,
        ex: Exchange,
        conn: sqlite3.Connection,
        *,
        equity: float,
        slippage_reserve: float,
        funding_reserve_per_8h: float,
        gap_reserve: float = 0.001,
    ) -> None:
        self.cfg = cfg
        self.meta = meta
        self.ex = ex
        self.conn = conn
        self.equity = equity
        self.starting_equity = equity
        self.slippage_reserve = slippage_reserve
        self.funding_reserve_per_8h = funding_reserve_per_8h
        self.gap_reserve = gap_reserve

        self.open_position: PaperPosition | None = None
        self._lock = threading.Lock()
        self._pending: object = None
        self._pending_prediction_id: str | None = None

    # --- public API --------------------------------------------------------

    def submit_entry(self, decision: object, prediction_id: str) -> None:
        """Queue an entry. Filled on the next tick."""
        with self._lock:
            if self.open_position is not None:
                log_event(self.conn, "paper_reject_entry", {
                    "reason": "position already open",
                    "prediction_id": prediction_id,
                })
                return
            self._pending = decision
            self._pending_prediction_id = prediction_id

    def tick(self, price: float) -> None:
        """Called from the main loop with the current price."""
        with self._lock:
            self._tick_locked(price)

    # --- internals ---------------------------------------------------------

    def _tick_locked(self, price: float) -> None:
        if self._pending is not None:
            self._fill_entry(self._pending, self._pending_prediction_id or "", price)
            self._pending = None
            self._pending_prediction_id = None
            return

        if self.open_position is None:
            return

        pos = self.open_position
        self._apply_funding(pos, now_utc())

        move = (price / pos.entry_price - 1.0) * (1 if pos.side == "long" else -1)

        if move <= -pos.stop_distance_pct:
            self._close(pos, price * (1 - self.gap_reserve)
                        if pos.side == "long"
                        else price * (1 + self.gap_reserve),
                        reason="stop")
        elif move >= pos.target_distance_pct:
            self._close(pos, price * (1 - self.slippage_reserve)
                        if pos.side == "long"
                        else price * (1 + self.slippage_reserve),
                        reason="target")

    def _fill_entry(
        self,
        decision: object,
        prediction_id: str,
        price: float,
    ) -> None:
        plan = decision.plan

        fill = price * (1 + self.slippage_reserve) if plan.side == "buy" \
            else price * (1 - self.slippage_reserve)
        entry_fee = self.meta.fees.taker * plan.quantity * fill
        side = "long" if plan.side == "buy" else "short"
        target_distance = 2.0 * plan.stop_distance_pct
        target_price = (
            fill * (1 + target_distance) if side == "long"
            else fill * (1 - target_distance)
        )
        self.open_position = PaperPosition(
            side=side,
            quantity=plan.quantity,
            entry_price=fill,
            entry_ts=now_utc(),
            stop_price=plan.stop_price,
            stop_distance_pct=plan.stop_distance_pct,
            target_price=target_price,
            target_distance_pct=target_distance,
            entry_fee=entry_fee,
            funding_paid=0.0,
            prediction_id=prediction_id,
            trade_id=str(uuid.uuid4()),
            last_funding_ts=now_utc(),
        )
        _persist_open(self.conn, self.open_position)

    def _close(self, pos: PaperPosition, price: float, reason: str) -> None:
        exit_fee = self.meta.fees.taker * pos.quantity * price
        direction = 1 if pos.side == "long" else -1
        gross = direction * (price - pos.entry_price) * pos.quantity
        realized = gross - pos.entry_fee - exit_fee - pos.funding_paid
        self.equity += realized
        _persist_close(self.conn, pos.trade_id, price, exit_fee, realized, reason,
                       self.equity)
        self.open_position = None

    def _apply_funding(self, pos: PaperPosition, now) -> None:
        elapsed = (now - pos.last_funding_ts).total_seconds()
        period = 8 * 3600
        if elapsed < period:
            return
        periods = int(elapsed // period)
        charge = self.funding_reserve_per_8h * pos.quantity * pos.entry_price * periods
        pos.funding_paid += charge
        pos.last_funding_ts = pos.last_funding_ts + timedelta(seconds=periods * period)


def _new_paper_id() -> str:
    return str(uuid.uuid4())


def _persist_open(conn: sqlite3.Connection, pos: PaperPosition) -> None:
    # Ensure prediction exists (for FK constraint)
    direction = 1 if pos.side == "long" else -1
    conn.execute(
        """INSERT OR IGNORE INTO predictions(
            prediction_id, decision_time, symbol, price, horizon_minutes,
            direction, confidence, expected_signed_return, expected_volatility,
            estimated_entry_fee, estimated_exit_fee, estimated_slippage,
            estimated_funding, expected_net_trade_return,
            risk_decision, rejection_reason,
            model_version, feature_version, config_version
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
(
                pos.prediction_id, to_iso(pos.entry_ts), "BTC/USDT:USDT", pos.entry_price,
                15, direction, 1.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0, "APPROVED", None,
                "paper-model", "paper-features", "paper-config",
            ),
    )
    conn.execute(
        """INSERT INTO paper_trades(
            trade_id, prediction_id, side, quantity, entry_price, entry_ts,
            stop_price, stop_distance_pct, target_distance_pct, entry_fee,
            funding_paid, equity_before
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pos.trade_id, pos.prediction_id, pos.side, pos.quantity,
            pos.entry_price, to_iso(pos.entry_ts),
            pos.stop_price, pos.stop_distance_pct, pos.target_distance_pct,
            pos.entry_fee, pos.funding_paid, 0.0,
        ),
    )
    log_event(conn, "paper_open", {
        "trade_id": pos.trade_id, "side": pos.side,
        "entry_price": pos.entry_price, "prediction_id": pos.prediction_id,
    })


def _persist_close(conn: sqlite3.Connection, trade_id: str, exit_price: float,
                   exit_fee: float, realized: float, reason: str, equity_after: float) -> None:
    conn.execute(
        """UPDATE paper_trades SET
             exit_price=?, exit_ts=?, exit_fee=?, realized_pnl=?,
             close_reason=?, equity_after=?
           WHERE trade_id=?""",
        (exit_price, to_iso(now_utc()), exit_fee, realized, reason, equity_after, trade_id),
    )
    log_event(conn, "paper_close", {
        "trade_id": trade_id, "exit_price": exit_price,
        "realized_pnl": realized, "reason": reason, "equity_after": equity_after,
    })