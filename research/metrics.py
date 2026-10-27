"""Signal quality metrics for backtesting.

Computes hit rate, mean signed return, confidence calibration, and
bootstrap confidence intervals for signal evaluation.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any


def _get(s: Any, key: str):
    """Get attribute from dict or dataclass."""
    if isinstance(s, dict):
        return s[key]
    return getattr(s, key)


@dataclass
class SignalMetrics:
    n: int
    hit_rate_15m: float
    hit_rate_60m: float
    mean_signed_return_15m: float
    mean_signed_return_60m: float
    # Confidence-bucketed metrics
    confidence_buckets: dict[str, dict[str, float]]

    def summary(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "hit_rate_15m": self.hit_rate_15m,
            "hit_rate_60m": self.hit_rate_60m,
            "mean_signed_return_15m": self.mean_signed_return_15m,
            "mean_signed_return_60m": self.mean_signed_return_60m,
            "confidence_buckets": self.confidence_buckets,
        }


def compute_signal_metrics(
    signals: list[dict[str, Any] | Any],
    confidence_buckets: list[tuple[float, float]] | None = None,
) -> SignalMetrics:
    """Compute signal quality metrics from a list of signal records.

    Each signal record must have:
        - direction: int (1 or -1)
        - confidence: float
        - expected_signed_return: float
        - signed_ret_15m: float (forward 15m return * direction)
        - signed_ret_60m: float (forward 60m return * direction)

    Args:
        signals: List of signal dicts.
        confidence_buckets: List of (low, high) confidence ranges for bucketing.
                           Default: [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.0)]

    Returns:
        SignalMetrics with all computed metrics.
    """
    if not signals:
        return SignalMetrics(
            n=0,
            hit_rate_15m=0.0,
            hit_rate_60m=0.0,
            mean_signed_return_15m=0.0,
            mean_signed_return_60m=0.0,
            confidence_buckets={},
        )

    if confidence_buckets is None:
        confidence_buckets = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.0)]

    n = len(signals)
    hit_15 = sum(1 for s in signals if _get(s, "signed_ret_15m") > 0)
    hit_60 = sum(1 for s in signals if _get(s, "signed_ret_60m") > 0)

    bucket_metrics = {}
    for low, high in confidence_buckets:
        bucket = [s for s in signals if low <= _get(s, "confidence") < high]
        if not bucket:
            bucket_metrics[f"{low:.1f}-{high:.1f}"] = {
                "n": 0,
                "hit_rate_15m": 0.0,
                "hit_rate_60m": 0.0,
                "mean_signed_return_15m": 0.0,
                "mean_signed_return_60m": 0.0,
                "mean_confidence": 0.0,
            }
            continue
        bucket_n = len(bucket)
        bucket_hit_15 = sum(1 for s in bucket if _get(s, "signed_ret_15m") > 0)
        bucket_hit_60 = sum(1 for s in bucket if _get(s, "signed_ret_60m") > 0)
        bucket_metrics[f"{low:.1f}-{high:.1f}"] = {
            "n": bucket_n,
            "hit_rate_15m": bucket_hit_15 / bucket_n,
            "hit_rate_60m": bucket_hit_60 / bucket_n,
            "mean_signed_return_15m": statistics.mean(_get(s, "signed_ret_15m") for s in bucket),
            "mean_signed_return_60m": statistics.mean(_get(s, "signed_ret_60m") for s in bucket),
            "mean_confidence": statistics.mean(_get(s, "confidence") for s in bucket),
        }

    return SignalMetrics(
        n=n,
        hit_rate_15m=hit_15 / n,
        hit_rate_60m=hit_60 / n,
        mean_signed_return_15m=statistics.mean(_get(s, "signed_ret_15m") for s in signals),
        mean_signed_return_60m=statistics.mean(_get(s, "signed_ret_60m") for s in signals),
        confidence_buckets=bucket_metrics,
    )


def bootstrap_metrics(
    signals: list[dict[str, Any] | Any],
    n_bootstrap: int = 1000,
    confidence_level: float = 0.9,
) -> dict[str, tuple[float, float]]:
    """Compute bootstrap confidence intervals for key metrics.

    Returns:
        Dict mapping metric name to (lower, upper) percentile bounds.
    """
    if not signals:
        return {}

    import random

    metrics_names = ["mean_signed_return_15m", "mean_signed_return_60m", "hit_rate_15m", "hit_rate_60m"]
    results = {m: [] for m in metrics_names}

    n = len(signals)
    for _ in range(n_bootstrap):
        sample = [signals[random.randrange(n)] for _ in range(n)]
        m = compute_signal_metrics(sample)
        results["mean_signed_return_15m"].append(m.mean_signed_return_15m)
        results["mean_signed_return_60m"].append(m.mean_signed_return_60m)
        results["hit_rate_15m"].append(m.hit_rate_15m)
        results["hit_rate_60m"].append(m.hit_rate_60m)

    alpha = (1.0 - confidence_level) / 2.0
    lower_pct = alpha
    upper_pct = 1.0 - alpha

    out = {}
    for m, vals in results.items():
        vals.sort()
        lower_idx = int(lower_pct * n_bootstrap)
        upper_idx = int(upper_pct * n_bootstrap)
        out[m] = (vals[lower_idx], vals[upper_idx])

    return out


def print_signal_metrics(metrics: SignalMetrics, bootstrap: dict | None = None, name: str = "Strategy") -> None:
    """Pretty-print signal metrics."""
    print(f"\n{'='*60}")
    print(f"Signal Quality: {name}")
    print(f"{'='*60}")
    print(f"  Total signals:           {metrics.n}")
    print(f"  Hit rate (15m):          {metrics.hit_rate_15m:.2%}")
    print(f"  Hit rate (60m):          {metrics.hit_rate_60m:.2%}")
    print(f"  Mean signed return (15m): {metrics.mean_signed_return_15m:.6f}")
    print(f"  Mean signed return (60m): {metrics.mean_signed_return_60m:.6f}")

    if bootstrap:
        print("\n  Bootstrap 90% CI:")
        for m, (lo, hi) in bootstrap.items():
            print(f"    {m}: [{lo:.6f}, {hi:.6f}]")

    print("\n  Confidence buckets:")
    for bucket, bm in metrics.confidence_buckets.items():
        if bm["n"] > 0:
            print(f"    {bucket}: n={bm['n']}, hit_15m={bm['hit_rate_15m']:.2%}, "
                  f"mean_ret_15m={bm['mean_signed_return_15m']:.6f}, "
                  f"mean_conf={bm['mean_confidence']:.3f}")