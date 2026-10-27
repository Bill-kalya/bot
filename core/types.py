"""Frozen contracts. Everything downstream depends on these.

Rule: no market fact (fee, min_notional, tick, step, leverage tier) is
defined here as a constant. Those arrive at runtime as MarketMeta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

# --- Signal contract (v0.2) -------------------------------------------------

@dataclass(frozen=True)
class Signal:
    decision_time: datetime
    symbol: str
    horizon_minutes: int

    direction: int                  # +1 long, -1 short, 0 hold
    confidence: float               # 0.0..1.0, intended to be calibrated

    expected_signed_return: float   # expected BTC return over horizon
    expected_volatility: float      # absolute vol over horizon

    source_version: str             # model_version from Config


# --- Exchange metadata (runtime, persisted) ---------------------------------

@dataclass(frozen=True)
class FeeSchedule:
    taker: float                    # e.g. 0.0005
    maker: float
    fetched_at: datetime


@dataclass(frozen=True)
class MarketMeta:
    symbol: str
    min_notional: float
    min_quantity: float
    quantity_step: float
    tick_size: float
    max_leverage: int
    fees: FeeSchedule
    fetched_at: datetime

    def to_json(self) -> dict[str, str | float | dict[str, str | float]]:
        from core.clock import to_iso
        return {
            "symbol": self.symbol,
            "min_notional": self.min_notional,
            "min_quantity": self.min_quantity,
            "quantity_step": self.quantity_step,
            "tick_size": self.tick_size,
            "max_leverage": self.max_leverage,
            "fees": {
                "taker": self.fees.taker,
                "maker": self.fees.maker,
                "fetched_at": to_iso(self.fees.fetched_at),
            },
            "fetched_at": to_iso(self.fetched_at),
        }


# --- Candle (normalized) ----------------------------------------------------

@dataclass(frozen=True)
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# --- Risk engine I/O --------------------------------------------------------

@dataclass(frozen=True)
class Plan:
    side: Literal["buy", "sell"]
    quantity: float
    notional: float
    leverage: int
    stop_price: float
    stop_distance_pct: float
    worst_case_loss: float


@dataclass(frozen=True)
class Approve:
    plan: Plan


@dataclass(frozen=True)
class RejectDecision:
    reason: str


Decision = Approve | RejectDecision


# --- Position (local cache; exchange is authoritative) ----------------------

@dataclass
class Position:
    symbol: str
    side: Literal["long", "short"]
    quantity: float
    entry_price: float
    opened_at: datetime
    stop_order_id: str | None = None
    entry_order_id: str | None = None
    prediction_id: str | None = None
    stop_distance_pct: float = 0.0
    target_distance_pct: float = 0.0


# --- Trade (durable accounting record) --------------------------------------

@dataclass
class Trade:
    trade_id: str
    prediction_id: str
    symbol: str
    side: Literal["long", "short"]
    quantity: float
    notional: float
    leverage: int

    opened_at: datetime
    closed_at: datetime | None

    entry_price: float
    exit_price: float | None

    stop_price: float
    stop_distance_pct: float
    target_distance_pct: float

    fees_paid: float
    funding_paid: float
    realized_pnl: float | None

    close_reason: str | None


# --- News (point-in-time) ----------------------------------------------------

@dataclass(frozen=True)
class NewsItem:
    news_id: str                    # canonical hash
    source: str                     # e.g. "coindesk-rss"
    source_item_id: str             # source's own identifier
    url: str
    title: str
    body: str

    event_time: datetime | None      # if the source claims one
    available_time: datetime            # when we could first have seen it
    ingested_at: datetime               # when we wrote it to our DB

    raw_hash: str                       # sha256 of the raw payload
    scorer_version: str                 # which scorer produced sentiment
    sentiment: float                    # -1..1
    relevance: float                    # 0..1, how much this is about our symbol
    event_type: str                     # "regulation", "listing", "macro", "other"

    source_reliability: float           # 0..1, configured per source
    superseded_by: str | None = None # news_id of a correction, if any


# --- Feature Vector (point-in-time) -------------------------------------------

@dataclass(frozen=True)
class FeatureVector:
    decision_time: datetime
    symbol: str
    feature_version: str

    # Market
    price: float
    returns_1m: float
    returns_5m: float
    returns_15m: float
    returns_60m: float
    volatility_15m: float
    volatility_60m: float
    volume_z_60m: float
    range_pct_last_1m: float
    above_sma_15m: float         # 0/1
    above_sma_60m: float         # 0/1
    rsi_14: float                # 0..100

    # News (aggregated over a lookback window that ends at decision_time)
    news_count_15m: int
    news_count_60m: int
    news_sentiment_mean_15m: float
    news_sentiment_mean_60m: float
    news_sentiment_max_abs_15m: float
    news_relevance_weighted_sentiment_15m: float
    news_regulation_flag_60m: float   # 0/1
    news_macro_flag_60m: float        # 0/1
    news_listing_flag_60m: float      # 0/1

    # Regime features (Tier 1)
    atr_14: float                     # average true range over 14 minutes, normalized by price
    volatility_percentile_60m: float  # 0..1, where current vol sits in last 60m
    trend_strength_60m: float         # abs(close - sma60) / sma60
    regime: str                       # one of: low_vol_chop, low_vol_trend, high_vol_chop, high_vol_trend


# --- Signal Study (multi-horizon) --------------------------------------------

@dataclass(frozen=True)
class SignalRecord:
    decision_time: datetime
    strategy: str
    direction: int
    confidence: float
    expected_signed_return: float
    entry_price: float
    forward_returns: dict[int, float] = field(default_factory=dict)  # horizon_minutes -> forward return
    signed_returns: dict[int, float] = field(default_factory=dict)  # horizon_minutes -> direction * forward


@dataclass
class SignalStudyResult:
    strategy: str
    records: list[SignalRecord] = field(default_factory=list)
    starting_candle_ts: datetime | None = None
    ending_candle_ts: datetime | None = None
    n_candles: int = 0
    n_signals: int = 0
    horizons: tuple[int, ...] = (15, 60, 240)