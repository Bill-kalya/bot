"""Metrics for the multi-horizon signal study.

All metrics are computed with bootstrap confidence intervals. The default is
1000 resamples at 5%/95%. If a metric's interval spans zero, the metric is
not distinguishable from chance at that confidence level.

Metrics per horizon:
  - hit_rate: fraction of signals where signed forward return > 0
  - mean_signed_return: mean of (direction * forward return)
  - median_signed_return: median of the same
  - expectancy: mean signed return divided by mean absolute return (edge ratio)
  - confidence_by_bucket: hit rate and mean signed return by confidence decile
  - long/short split: hit rate and mean signed return separately
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

DEFAULT_HORIZONS: tuple[int, ...] = (15, 60, 240)


@dataclass
class BootstrapInterval:
    point: float
    low: float
    high: float
    n: int
    n_bootstrap: int


def bootstrap_mean(
    values: list[float], *, n_bootstrap: int = 1000, alpha: float = 0.05,
    rng: random.Random | None = None,
) -> BootstrapInterval:
    if not values:
        return BootstrapInterval(0.0, 0.0, 0.0, 0, n_bootstrap)
    rng = rng or random.Random(42)
    n = len(values)
    point = statistics.mean(values)
    samples = []
    for _ in range(n_bootstrap):
        resample = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(statistics.mean(resample))
    samples.sort()
    lo = samples[int(alpha / 2 * n_bootstrap)]
    hi = samples[int((1 - alpha / 2) * n_bootstrap) - 1]
    return BootstrapInterval(point, lo, hi, n, n_bootstrap)


def bootstrap_hit_rate_hits(hits: list[float], *, n_bootstrap: int = 1000,
    alpha: float = 0.05, rng: random.Random | None = None) -> BootstrapInterval:
    if not hits:
        return BootstrapInterval(0.0, 0.0, 0.0, 0, n_bootstrap)
    rng = rng or random.Random(42)
    n = len(hits)
    point = sum(hits) / n
    samples = []
    for _ in range(n_bootstrap):
        s = sum(hits[rng.randrange(n)] for _ in range(n)) / n
        samples.append(s)
    samples.sort()
    lo = samples[int(alpha / 2 * n_bootstrap)]
    hi = samples[int((1 - alpha / 2) * n_bootstrap) - 1]
    return BootstrapInterval(point, lo, hi, n, n_bootstrap)


def _expectancy(values: list[float]) -> float:
    if not values:
        return 0.0
    mean_abs = statistics.mean(abs(v) for v in values)
    if mean_abs == 0:
        return 0.0
    return statistics.mean(values) / mean_abs


def confidence_buckets(
    records: list, horizon: int, *, n_buckets: int = 5,
) -> list[dict]:
    """Bucket records by confidence, using returns at the given horizon."""
    if not records:
        return []
    sorted_recs = sorted(records, key=lambda r: r.confidence)
    n = len(sorted_recs)
    size = max(1, n // n_buckets)
    out = []
    for i in range(n_buckets):
        start = i * size
        end = n if i == n_buckets - 1 else (i + 1) * size
        chunk = sorted_recs[start:end]
        if not chunk:
            continue
        hit = sum(1 for r in chunk if r.signed_returns[horizon] > 0) / len(chunk)
        mean = statistics.mean(r.signed_returns[horizon] for r in chunk)
        out.append({
            "bucket": i + 1,
            "n": len(chunk),
            "hit_rate": hit,
            "mean_signed_return": mean,
        })
    return out


def summarize(
    result,  # SignalStudyResult
    horizons: tuple[int, ...] | None = None,
) -> dict:
    """Return a horizon-keyed summary.

    Example output:
      {
        "strategy": "news",
        "n_signals": 177,
        "by_horizon": {
          15: {"hit_rate": {...}, "mean_signed_return": {...}, ...},
          60: {...},
          240: {...},
        },
        "confidence_buckets": {15: [...], 60: [...], 240: [...]},
      }
    """
    horizons = horizons or (15, 60, 240)
    records = result.records
    if not records:
        return {
            "strategy": result.strategy,
            "n_signals": 0,
            "note": "no signals emitted",
            "by_horizon": {},
            "confidence_buckets": {},
        }

    out = {
        "strategy": result.strategy,
        "n_signals": len(records),
        "n_candles": result.n_candles,
        "window_start": str(result.starting_candle_ts),
        "window_end": str(result.ending_candle_ts),
        "by_horizon": {},
        "confidence_buckets": {},
    }

    for h in horizons:
        if not all(h in r.signed_returns for r in records):
            continue
        signed = [r.signed_returns[h] for r in records]
        hits = [1.0 if s > 0 else 0.0 for s in signed]
        
        hit_h = bootstrap_hit_rate_hits(hits)
        mean_h = bootstrap_mean(signed)
        
        out["by_horizon"][h] = {
            "hit_rate": {
                "point": hit_h.point, "low": hit_h.low, "high": hit_h.high,
            },
            "mean_signed_return": {
                "point": mean_h.point, "low": mean_h.low, "high": mean_h.high,
            },
            "median_signed_return": statistics.median(signed),
            "expectancy": _expectancy(signed),
            "long_count": sum(1 for r in result.records if r.direction > 0),
            "short_count": sum(1 for r in result.records if r.direction < 0),
        }
        out["confidence_buckets"][h] = confidence_buckets(records, h)

    return out


def print_signal_metrics(metrics: dict, horizons: tuple[int, ...] = (15, 60, 240), name: str = "Strategy") -> None:
    """Pretty-print signal metrics."""
    print(f"\n{'='*60}")
    print(f"Signal Quality: {name}")
    print(f"{'='*60}")
    print(f"  Total signals:           {metrics['n_signals']}")
    
    for h in horizons:
        bh = metrics["by_horizon"].get(h)
        if not bh:
            continue
        print(f"\n  Horizon {h}m:")
        print(f"  Hit rate:          {bh['hit_rate']['point']:.2%} [{bh['hit_rate']['low']:.2%}, {bh['hit_rate']['high']:.2%}]")
        print(f"  Mean signed return: {bh['mean_signed_return']['point']:.6f} [{bh['mean_signed_return']['low']:.6f}, {bh['mean_signed_return']['high']:.6f}]")
        print(f"  Expectancy:        {bh['expectancy']:.3f}")

    if metrics.get("confidence_buckets"):
        print("\n  Confidence buckets:")
        for h in horizons:
            buckets = metrics["confidence_buckets"].get(h, [])
            if not buckets:
                continue
            print(f"  Horizon {h}m:")
            for bm in buckets:
                if bm["n"] > 0:
                    print(f"    {bm['bucket']}: n={bm['n']}, hit={bm['hit_rate']:.2%}, mean_ret={bm['mean_signed_return']:.6f}")


# Convenience: summarize a flat list of records (bypasses SignalStudyResult)
def summarize_flat(records, strategy_name: str, horizons: tuple[int, ...] = (15, 60, 240)) -> dict:
    from research.signal_study import SignalStudyResult
    r = SignalStudyResult(strategy=strategy_name, horizons=tuple(horizons))
    r.records = records
    r.n_signals = len(records)
    return summarize(r, horizons)