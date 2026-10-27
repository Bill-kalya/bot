"""Signal quality study, multi-horizon.

For each strategy, walk a historical candle stream. At every decision point,
build features, call the strategy, and record forward returns at multiple
horizons.

The signal's own `horizon_minutes` is separate from the study's evaluation
horizons. The signal declares what it was designed for (used by the risk
engine); the study records outcomes at (15, 60, 240) regardless. This lets
us ask "does the same signal predict returns over different time windows?"
without changing the signal.

No risk engine. No fees. No account size. Pure information test.
"""
from __future__ import annotations

import logging

from core.types import Candle, SignalRecord, SignalStudyResult

log = logging.getLogger(__name__)


DEFAULT_HORIZONS: tuple[int, ...] = (15, 60, 240)


def run_signal_study(
    candles: list[Candle],
    news_at,
    strategy_fn,
    build_features_fn,
    symbol: str,
    strategy_name: str,
    *,
    window_size: int = 60,
    horizons: tuple[int, ...] = (15, 60, 240),
) -> SignalStudyResult:
    """Walk candles, emit signals, record forward outcomes at each horizon.

    news_at(decision_time) -> list[NewsItem] with available_time <= decision_time
    build_features_fn(candles_window, news, decision_time, symbol) -> FeatureVector
    """
    from core.types import SignalStudyResult

    result = SignalStudyResult(strategy=strategy_name, horizons=tuple(horizons))
    if not horizons:
        return result

    max_h = max(horizons)
    if len(candles) < window_size + max_h + 1:
        return result

    result.starting_candle_ts = candles[window_size].ts
    result.ending_candle_ts = candles[-max_h - 1].ts
    result.n_candles = len(candles)

    for i in range(window_size, len(candles) - max_h):
        window = candles[i - window_size:i]
        decision_time = window[-1].ts
        news = news_at(decision_time)

        features = build_features_fn(window, news, decision_time, symbol)
        signal = strategy_fn(features)

        if signal.direction == 0:
            continue

        entry = window[-1].close
        fwd: dict[int, float] = {}
        signed: dict[int, float] = {}
        ok = True
        for h in horizons:
            j = i + h - 1
            if j >= len(candles):
                ok = False
                break
            r = candles[j].close / entry - 1.0
            fwd[h] = r
            signed[h] = signal.direction * r
        if not ok:
            continue

        result.records.append(SignalRecord(
            decision_time=decision_time,
            strategy=strategy_name,
            direction=signal.direction,
            confidence=signal.confidence,
            expected_signed_return=signal.expected_signed_return,
            entry_price=entry,
            forward_returns=fwd,
            signed_returns=signed,
        ))

    result.n_signals = len(result.records)
    return result