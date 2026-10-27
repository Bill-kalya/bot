"""Phase 9 experiment driver.

Runs:
  Experiment 1 (signal quality): 4 strategies, walk-forward windows,
    bootstrap CIs on hit rate and mean signed return at multiple horizons.
  Experiment 2 (net economics): 4 strategies x 3 account sizes,
    full pipeline, walk-forward windows (single horizon).

Writes results to research/out/phase9_{timestamp}/ with:
  - summary.json   machine-readable
  - summary.md     human-readable
  - signals.jsonl  every individual signal record (Experiment 1)
  - trades.jsonl   every individual trade (Experiment 2)
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

from config import Config
from core.types import Candle, MarketMeta
from data.features import build_features
from research.account_sweep import run_sweep
from research.signal_metrics import summarize, summarize_flat
from research.signal_study import run_signal_study
from research.walk_forward import make_windows

log = logging.getLogger(__name__)


def run_phase9(
    cfg: Config,
    meta: MarketMeta,
    candles: list[Candle],
    news_lookup,
    strategies: dict,
    *,
    n_windows: int = 5,
    account_sizes: list[float] | None = None,
    horizons: tuple[int, ...] = (15, 60, 240),
    out_dir: Path,
) -> dict:
    if account_sizes is None:
        account_sizes = [10.0, 100.0, 1000.0]
    out_dir.mkdir(parents=True, exist_ok=True)

    windows = make_windows(candles, n_windows)

    report: dict = {
        "config": {
            "symbol": cfg.symbol,
            "model_version": cfg.model_version,
            "feature_version": cfg.feature_version,
            "config_version": cfg.config_version,
            "n_candles": len(candles),
            "n_windows": n_windows,
            "account_sizes": account_sizes,
            "horizons": list(horizons),
        },
        "experiment_1": {},
        "experiment_2": {},
        "windows": [
            {"index": w.index, "start": str(w.start_ts), "end": str(w.end_ts)}
            for w in windows
        ],
    }

    # ----- Experiment 1: signal quality (multi-horizon) -----------------
    log.info("experiment 1: signal quality (multi-horizon)")
    for name, strategy_fn in strategies.items():
        log.info("  strategy=%s", name)
        per_window = []
        all_records = []
        for w in windows:
            window_candles = candles[w.start_idx:w.end_idx]
            total_candles = len(window_candles)
            print(f"    [{name}] window {w.index+1}/{len(windows)}: {total_candles} candles", file=sys.stderr)
            # window_size must be >= max(horizons) + 1 for features to compute correctly
            window_size = max(horizons) + 1
            result = run_signal_study(
                window_candles, news_lookup, strategy_fn, build_features,
                cfg.symbol, name, window_size=window_size, horizons=horizons,
            )
            per_window.append(summarize(result, horizons))
            all_records.extend(result.records)

        pooled = summarize_flat(all_records, name, horizons)
        report["experiment_1"][name] = {
            "per_window": per_window,
            "pooled": pooled,
        }

        # Dump individual records
        with (out_dir / f"signals_{name}.jsonl").open("w") as f:
            for r in all_records:
                f.write(json.dumps(_to_jsonable(asdict(r))) + "\n")

    # ----- Experiment 2: net economics (single horizon) ---------------
    log.info("experiment 2: account sweep")
    for name, strategy_fn in strategies.items():
        log.info("  strategy=%s", name)
        sweep = run_sweep(
            cfg, meta, candles, news_lookup, strategy_fn, build_features,
            account_sizes,
        )
        report["experiment_2"][name] = [asdict(s) for s in sweep]

    # ----- write outputs -----------------------------------------------
    (out_dir / "summary.json").write_text(
        json.dumps(_to_jsonable(report), indent=2)
    )
    (out_dir / "summary.md").write_text(_render_markdown(report))
    return report


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)


def _render_markdown(report: dict) -> str:
    horizons = report["config"].get("horizons", [15])
    lines = ["# Phase 9 — A/B Experiments", ""]
    lines.append(f"Symbol: `{report['config']['symbol']}`")
    lines.append(f"Candles: `{report['config']['n_candles']}`")
    lines.append(f"Windows: `{report['config']['n_windows']}`")
    lines.append(f"Horizons (min): {', '.join(str(h) for h in horizons)}")
    lines.append("")

    for h in horizons:
        lines.append(f"## Experiment 1 — Signal quality, horizon {h}m")
        lines.append("")
        lines.append("| Strategy | N signals | Hit rate | Mean signed ret | Expectancy |")
        lines.append("|---|---:|---:|---:|---:|")
        for name, data in report["experiment_1"].items():
            p = data["pooled"]
            if p.get("n_signals", 0) == 0:
                lines.append(f"| {name} | 0 | — | — | — |")
                continue
            bh = p.get("by_horizon", {}).get(str(h)) or p.get("by_horizon", {}).get(h)
            if not bh:
                lines.append(f"| {name} | {p['n_signals']} | (no data) | | |")
                continue
            hr = bh["hit_rate"]
            mr = bh["mean_signed_return"]
            lines.append(
                f"| {name} | {p['n_signals']} | "
                f"{hr['point']:.3f} [{hr['low']:.3f}, {hr['high']:.3f}] | "
                f"{mr['point']:.5f} [{mr['low']:.5f}, {mr['high']:.5f}] | "
                f"{bh['expectancy']:.3f} |"
            )
        lines.append("")

    lines.append("## Experiment 2 — Account sweep (single horizon)")
    lines.append("")
    lines.append("| Strategy | Equity | Trades | Wins | Losses | P&L | Fees | Max DD |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for name, rows in report["experiment_2"].items():
        for r in rows:
            lines.append(
                f"| {name} | ${r['starting_equity']:.0f} | {r['n_trades']} | "
                f"{r['n_wins']} | {r['n_losses']} | {r['total_pnl']:.5f} | "
                f"{r['total_fees']:.5f} | {r['max_drawdown_pct']:.2%} |"
            )
    lines.append("")
    return "\n".join(lines)


