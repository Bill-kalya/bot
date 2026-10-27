"""Env-driven configuration. Single source of truth for tunables.

Nothing here is a market fact (fees, min_notional, tick, step). Those come
from the exchange at runtime via exchange/metadata.py. This file only holds
policy and identity.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent


def _parse_feeds(env: str) -> list[tuple[str, str, float]]:
    """Format: name|url|reliability;name2|url2|rel2"""
    if not env:
        return [
            ("coindesk-rss", "https://www.coindesk.com/arc/outboundfeeds/rss/", 0.6),
            ("cointelegraph-rss", "https://cointelegraph.com/rss", 0.5),
        ]
    out = []
    for part in env.split(";"):
        part = part.strip()
        if not part:
            continue
        name, url, rel = part.split("|")
        out.append((name.strip(), url.strip(), float(rel)))
    return out


@dataclass(frozen=True)
class Config:
    # Identity / versioning — every prediction row records these.
    model_version: str
    feature_version: str
    config_version: str

    # Market
    symbol: str

    # Environment
    demo: bool
    exchange_id: str

    # Ledger
    start_equity: float
    ledger_path: Path

    # Risk policy (research constraints — NOT production defaults)
    max_leverage: int
    max_loss_per_trade_pct: float
    daily_loss_cap_pct: float
    min_confidence: float
    min_edge: float

    # Stop distance (fixed % from entry, not derived from equity)
    stop_distance_pct: float = 0.02

    # Cost reserves (used by risk engine; overridable by realised data later)
    slippage_reserve: float = 0.0005
    funding_reserve: float = 0.0002
    latency_reserve: float = 0.0002
    stop_slippage_reserve: float = 0.0010

    # Loop
    loop_seconds: int = 30
    candle_limit: int = 60

    # Reconciliation
    reconcile_every_loops: int = 20
    funding_lookback_hours: int = 24

    # Labeling
    label_every_loops: int = 40

    # News
    news_feeds: list[tuple[str, str, float]] = None  # type: ignore
    news_poll_seconds: int = 300

    # Strategy
    strategy_name: str = "momentum"
    news_lookback_minutes: int = 120

    # Shadow mode
    shadow_mode: bool = True

    # Paper-only live data mode: real market data, paper execution, no real orders
    paper_only: bool = True

    # Enable verbose risk engine logging (diagnostic)
    log_risk_evaluations: bool = False

    # Tier 1 experiment flags
    exit_mode: str = "stop_target"    # "stop_target" | "fixed_horizon"
    hold_minutes: int = 60             # horizon for fixed_horizon mode
    regime_filter_enabled: bool = False  # enables strategy/news_model_filtered.py

    # Paths
    stop_file: Path = Path("STOP")
    state_dir: Path = Path("state")

    @classmethod
    def from_env(cls) -> Config:
        # paper_only and shadow_mode are mutually exclusive: shadow mode
        # assumes real orders are being placed and paper is comparing. If
        # paper_only is on, there are no real orders, so shadow mode is
        # silently disabled.
        paper_only = os.getenv("PAPER_ONLY", "true").lower() == "true"
        shadow_mode = os.getenv("SHADOW_MODE", "true").lower() == "true"
        if paper_only:
            shadow_mode = False

        return cls(
            model_version=os.getenv("MODEL_VERSION", "momentum-v0.2.0"),
            feature_version=os.getenv("FEATURE_VERSION", "features-v0.2.0"),
            config_version=os.getenv("CONFIG_VERSION", "config-v0.2.0"),

            symbol=os.getenv("SYMBOL", "BTC/USDT:USDT"),
            demo=os.getenv("DEMO", "true").lower() == "true",
            exchange_id=os.getenv("EXCHANGE_ID", "binanceusdm"),

            start_equity=float(os.getenv("START_EQUITY", "10")),
            ledger_path=ROOT / "state" / "ledger.sqlite",

            max_leverage=int(os.getenv("MAX_LEVERAGE", "20")),
            max_loss_per_trade_pct=float(os.getenv("MAX_LOSS_PER_TRADE_PCT", "0.20")),
            daily_loss_cap_pct=float(os.getenv("DAILY_LOSS_CAP_PCT", "0.30")),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.30")),
            min_edge=float(os.getenv("MIN_EDGE", "0.0005")),  # net, after all costs

            stop_distance_pct=float(os.getenv("STOP_DISTANCE_PCT", "0.02")),

            slippage_reserve=float(os.getenv("SLIPPAGE_RESERVE", "0.0005")),
            funding_reserve=float(os.getenv("FUNDING_RESERVE", "0.0002")),
            latency_reserve=float(os.getenv("LATENCY_RESERVE", "0.0002")),
            stop_slippage_reserve=float(os.getenv("STOP_SLIPPAGE_RESERVE", "0.0010")),

            loop_seconds=int(os.getenv("LOOP_SECONDS", "30")),
            candle_limit=int(os.getenv("CANDLE_LIMIT", "60")),

            reconcile_every_loops=int(os.getenv("RECONCILE_EVERY_LOOPS", "20")),
            funding_lookback_hours=int(os.getenv("FUNDING_LOOKBACK_HOURS", "24")),

            label_every_loops=int(os.getenv("LABEL_EVERY_LOOPS", "40")),

            news_feeds=_parse_feeds(os.getenv("NEWS_FEEDS", "")),
            news_poll_seconds=int(os.getenv("NEWS_POLL_SECONDS", "300")),

            strategy_name=os.getenv("STRATEGY", "momentum"),
            news_lookback_minutes=int(os.getenv("NEWS_LOOKBACK_MINUTES", "120")),

            shadow_mode=shadow_mode,

            paper_only=paper_only,

            log_risk_evaluations=os.getenv("LOG_RISK_EVALUATIONS", "false").lower() == "true",

            exit_mode=os.getenv("EXIT_MODE", "stop_target"),
            hold_minutes=int(os.getenv("HOLD_MINUTES", "60")),
            regime_filter_enabled=os.getenv("REGIME_FILTER_ENABLED", "false").lower() == "true",

            stop_file=ROOT / "STOP",
            state_dir=ROOT / "state",
        )

    def kill_switch_active(self) -> bool:
        return self.stop_file.exists()