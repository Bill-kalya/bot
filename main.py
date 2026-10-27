"""Phase 8 entrypoint.

Changes from Phase 7:
  - Shadow mode: Paper executor runs in parallel with demo exchange.
  - Divergence tracking for entry/exit price and fee differences.
  - Divergence report available via scripts/divergence_report.py.
  - Paper-only live data mode: real market data, paper execution, no real orders.
"""
from __future__ import annotations

import logging
import os
import time
from enum import Enum

from config import Config
from core.clock import now_utc, to_iso
from core.errors import Halt
from core.types import Approve, Position
from data.features import build_features
from data.news.pipeline import ingest
from data.news.rss_collector import RSSCollector
from exchange.fake_adapter import FakeExchange, default_fake_meta
from execution.divergence import record_entry_divergence
from execution.funding import apply_funding
from execution.orders import close_position, open_position
from execution.paper import PaperExecutor
from execution.reconcile import reconcile, should_reconcile
from research.labeler import label_pending
from risk.account import Account
from risk.engine import evaluate
from storage.db import connect, init_schema
from storage.ledger import Ledger
from storage.logger import log_event, log_prediction
from storage.news import get_news_available_at
from strategy import baseline
from strategy.registry import get as get_strategy

log = logging.getLogger(__name__)


def _assert_paper_only_is_safe(cfg: Config) -> None:
    if cfg.paper_only and not cfg.demo:
        raise Halt("PAPER_ONLY=true requires DEMO=true "
                   "(we never trade mainnet in this configuration)")


class State(str, Enum):
    STARTING = "STARTING"
    RECOVERING = "RECOVERING"
    MONITORING = "MONITORING"
    EVALUATING = "EVALUATING"
    ENTERING = "ENTERING"
    PROTECTED = "PROTECTED"
    EXITING = "EXITING"
    HALTED = "HALTED"


def _build_exchange(cfg: Config):
    import os
    if os.getenv("USE_FAKE", "true").lower() == "true":
        return FakeExchange(default_fake_meta(cfg.symbol))
    from exchange.ccxt_adapter import CcxtExchange
    return CcxtExchange(cfg)


def _log_state(conn, state: State, **extra) -> None:
    log_event(conn, "state", {"state": state.value, **extra})
    log.info("state=%s %s", state.value, extra)


def _recover_position(exchange_positions, conn) -> Position | None:
    if not exchange_positions:
        return None
    p = exchange_positions[0]
    position = Position(
        symbol=p.get("symbol", ""),
        side=p["side"],
        quantity=p["quantity"],
        entry_price=p["entry_price"],
        opened_at=now_utc(),
        stop_order_id=p["stop_order_id"],
        entry_order_id=None,
        prediction_id=None,
        # We cannot recover stop_distance_pct from the exchange. Reconciliation
        # guarantees the stop exists, but for exit management we fall back to a
        # conservative default and log the gap.
        stop_distance_pct=0.02,
        target_distance_pct=0.04,
    )
    log_event(conn, "recovered_position", {
        "side": position.side,
        "qty": position.quantity,
        "stop_id": position.stop_order_id,
        "note": "stop_distance_pct defaulted after recovery",
    })
    return position


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    cfg = Config.from_env()
    cfg.state_dir.mkdir(parents=True, exist_ok=True)

    conn = connect(cfg.ledger_path)
    init_schema(conn)
    ledger = Ledger(conn, start_equity=cfg.start_equity)

    state = State.STARTING
    _log_state(conn, state)

    ex = _build_exchange(cfg)
    ex.load_markets()
    meta = ex.fetch_market_meta(cfg.symbol)

    # Guard: paper_only requires demo
    _assert_paper_only_is_safe(cfg)

    # Log config for audit
    log_event(conn, "config", {
        "paper_only": cfg.paper_only,
        "shadow_mode": cfg.shadow_mode,
        "demo": cfg.demo,
        "use_fake": os.getenv("USE_FAKE", "true"),
    })

    state = State.RECOVERING
    _log_state(conn, state)
    # In paper_only mode, skip reconciliation (no real positions to recover)
    if cfg.paper_only:
        reconciled = []
        log_event(conn, "reconcile_skipped", {"reason": "paper_only mode"})
    else:
        reconciled = reconcile(ex, cfg, conn)
    current_position = _recover_position(reconciled, conn)

    # Apply any funding that accrued while we were down.
    if not cfg.paper_only:
        apply_funding(ex, cfg, ledger, conn)

    state = State.MONITORING
    _log_state(conn, state)

    # --- paper executor (always runs in paper_only mode) ---------------------
    paper = PaperExecutor(
        cfg, meta, ex, conn,
        equity=cfg.start_equity,
        slippage_reserve=cfg.slippage_reserve,
        funding_reserve_per_8h=cfg.funding_reserve,
        gap_reserve=0.001,
    )

    # Collectors for news
    collectors = [
        RSSCollector(name, url, source_reliability=rel)
        for (name, url, rel) in cfg.news_feeds
    ]

    # Track when we last fetched news
    last_news_fetch = 0.0

    state = State.MONITORING
    _log_state(conn, state)

    loop_index = 0

    while state != State.HALTED:
        try:
            if cfg.kill_switch_active():
                _log_state(conn, State.HALTED, reason="STOP file present")
                state = State.HALTED
                break

            # --- recurring reconciliation ---------------------------------
            if should_reconcile(loop_index, cfg) and not cfg.paper_only:
                try:
                    reconcile(ex, cfg, conn)
                except Halt as e:
                    _log_state(conn, State.HALTED, reason=f"reconcile: {e}")
                    state = State.HALTED
                    break

            # --- periodic labeling ----------------------------------------
            if cfg.label_every_loops > 0 and loop_index % cfg.label_every_loops == 0:
                try:
                    n = label_pending(ex, conn, cfg.symbol)
                    if n:
                        log_event(conn, "labeled", {"count": n})
                except Exception as e:  # noqa: BLE001
                    log_event(conn, "label_failed", {"error": str(e)})

            # --- capture decision time BEFORE fetching market data ---
            decision_time = now_utc()
            now_iso = to_iso(decision_time)

            candles = ex.fetch_ohlcv(cfg.symbol, "1m", cfg.candle_limit)
            price = ex.fetch_price(cfg.symbol)

            # --- get news available at this decision time -----------------
            recent_news = get_news_available_at(conn, now_iso, limit=200)
            log_event(conn, "news_available", {"count": len(recent_news)})

            # --- manage existing position ---------------------------------
            if current_position is not None:
                move = (
                    (price / current_position.entry_price - 1.0)
                    * (1 if current_position.side == "long" else -1)
                )
                recent_news = get_news_available_at(conn, now_iso, limit=200)
                features = build_features(
                    candles=candles,
                    news=recent_news,
                    decision_time=decision_time,
                    symbol=cfg.symbol,
                )
                signal = baseline.predict(candles, cfg.symbol, cfg.model_version)
                flipped = (
                    signal.direction != 0
                    and (signal.direction > 0) != (current_position.side == "long")
                )
                if (
                    move <= -current_position.stop_distance_pct
                    or move >= current_position.target_distance_pct
                    or flipped
                ):
                    state = State.EXITING
                    _log_state(conn, state, reason="exit condition",
                               move=move, flipped=flipped)
                    if cfg.paper_only:
                        paper.close_position(reason=f"move={move:.4f} flipped={flipped}")
                    else:
                        close_position(
                            ex, cfg, conn, current_position,
                            reason=f"move={move:.4f} flipped={flipped}",
                        )
                    current_position = None
                    state = State.MONITORING
                    _log_state(conn, state)
                    loop_index += 1
                    time.sleep(cfg.loop_seconds)
                    continue

            # --- evaluate new entries when flat ----------------------------
            else:
                state = State.EVALUATING
                _log_state(conn, state)
                recent_news = get_news_available_at(conn, now_iso, limit=200)
                features = build_features(
                    candles=candles,
                    news=recent_news,
                    decision_time=decision_time,
                    symbol=cfg.symbol,
                )
                strategy_fn = get_strategy(cfg.strategy_name)
                signal = strategy_fn(features)

                account = Account(
                    equity=ledger.equity,
                    daily_baseline=ledger.daily_baseline,
                    peak_equity=ledger.peak_equity,
                    open_positions=0 if cfg.demo else len(ex.fetch_positions(cfg.symbol)),
                )
                decision, costs = evaluate(signal, account, meta, price, cfg)

                # Log the decision for visibility
                if isinstance(decision, Approve):
                    log.info("approved: side=%s qty=%.6f notional=%.2f leverage=%d stop_dist=%.4f conf=%.2f",
                             decision.plan.side, decision.plan.quantity,
                             decision.plan.notional, decision.plan.leverage,
                             decision.plan.stop_distance_pct, signal.confidence)
                else:
                    log.info("rejected: %s", decision.reason)

                pid = log_prediction(
                    conn,
                    signal=signal,
                    price=price,
                    decision=decision,
                    estimated_entry_fee=costs.entry_fee,
                    estimated_exit_fee=costs.exit_fee,
                    estimated_slippage=costs.slippage,
                    estimated_funding=costs.funding,
                    expected_net_trade_return=(
                        signal.direction * signal.expected_signed_return - costs.total
                    ),
                    model_version=cfg.model_version,
                    feature_version=cfg.feature_version,
                    config_version=cfg.config_version,
                )

                if isinstance(decision, Approve):
                    state = State.ENTERING
                    _log_state(conn, state, prediction_id=pid)

                    if cfg.paper_only:
                        # No real order. Feed the decision to the paper executor.
                        if paper is not None:
                            paper.open_position(decision, pid, meta=meta)
                        log_event(conn, "paper_only_skip_real_order", {
                            "prediction_id": pid,
                            "note": "PAPER_ONLY=true; decision routed to paper only",
                        })
                        state = State.MONITORING
                        _log_state(conn, state)
                        # Do not set current_position. The paper executor owns
                        # the simulated position; the real account stays flat.
                        loop_index += 1
                        time.sleep(cfg.loop_seconds)
                        continue

                    current_position = open_position(ex, cfg, conn, decision, pid, meta=meta)
                    state = State.PROTECTED
                    _log_state(conn, state, stop_id=current_position.stop_order_id)
                    state = State.MONITORING
                    _log_state(conn, state)
                else:
                    log_event(conn, "rejected", {
                        "prediction_id": pid, "reason": decision.reason,
                    })

            # --- paper tick (shadow mode) ----------------------------------
            if paper is not None:
                paper.tick(price)

            # --- record entry divergence ------------------------------------
            # Only in shadow mode (not paper_only) since we need a real order to compare against
            if isinstance(decision, Approve) and paper is not None and not cfg.paper_only:
                # The paper fill happened on the previous tick; the demo
                # fill is now. We record both.
                row = conn.execute(
                    "SELECT entry_price FROM paper_trades WHERE prediction_id=?",
                    (pid,),
                ).fetchone()
                if row is not None:
                    record_entry_divergence(
                        conn,
                        prediction_id=pid,
                        paper_price=row["entry_price"],
                        demo_price=current_position.entry_price,
                        paper_fee=meta.fees.taker * current_position.quantity * row["entry_price"],
                        demo_fee=meta.fees.taker * current_position.quantity * current_position.entry_price,
                        demo_latency_ms=int((time.monotonic() - time.monotonic()) * 1000),  # placeholder
                    )

            # --- periodic news fetch ---------------------------------------
            if time.monotonic() - last_news_fetch >= cfg.news_poll_seconds:
                try:
                    for c in collectors:
                        result = ingest(conn, c)
                        log_event(conn, "news_ingest", result)
                except Exception as e:  # noqa: BLE001
                    log_event(conn, "news_fetch_failed", {"error": str(e)})

            loop_index += 1
            time.sleep(cfg.loop_seconds)

        except Halt as e:
            _log_state(conn, State.HALTED, reason=str(e))
            state = State.HALTED
        except KeyboardInterrupt:
            _log_state(conn, State.HALTED, reason="keyboard interrupt")
            state = State.HALTED
        except Exception as e:  # noqa: BLE001
            _log_state(conn, State.HALTED, reason=f"unexpected: {e!r}")
            state = State.HALTED

    log_event(conn, "shutdown", {"final_state": state.value})


if __name__ == "__main__":
    run()