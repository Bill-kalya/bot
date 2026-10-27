from datetime import UTC, datetime

from core.types import FeatureVector
from strategy.news_model_filtered import predict


def _fv(**over):
    base = {
        "decision_time": datetime(2026, 1, 1, tzinfo=UTC),
        "symbol": "BTC/USDT:USDT", "feature_version": "features-v0.2.0",
        "price": 60_000.0,
        "returns_1m": 0.0, "returns_5m": 0.0, "returns_15m": 0.0, "returns_60m": 0.0,
        "volatility_15m": 0.002, "volatility_60m": 0.003,
        "volume_z_60m": 0.0, "range_pct_last_1m": 0.001,
        "above_sma_15m": 0.0, "above_sma_60m": 0.0, "rsi_14": 50.0,
        "news_count_15m": 0, "news_count_60m": 0,
        "news_sentiment_mean_15m": 0.0, "news_sentiment_mean_60m": 0.0,
        "news_sentiment_max_abs_15m": 0.0,
        "news_relevance_weighted_sentiment_15m": 0.0,
        "news_regulation_flag_60m": 0.0, "news_macro_flag_60m": 0.0,
        "news_listing_flag_60m": 0.0,
        "atr_14": 0.0, "volatility_percentile_60m": 0.5, "trend_strength_60m": 0.0,
        "regime": "low_vol_chop",
    }
    base.update(over)
    return FeatureVector(**base)


def test_filtered_fires_in_high_vol_regime():
    fv = _fv(regime="high_vol_chop",
             news_relevance_weighted_sentiment_15m=0.5, news_count_15m=3)
    sig = predict(fv)
    assert sig.direction == 1


def test_filtered_holds_in_low_vol_regime():
    fv = _fv(regime="low_vol_chop",
             news_relevance_weighted_sentiment_15m=0.5, news_count_15m=3)
    sig = predict(fv)
    assert sig.direction == 0


def test_filtered_holds_without_news():
    fv = _fv(regime="high_vol_chop")
    sig = predict(fv)
    assert sig.direction == 0


def test_filtered_horizon_is_60():
    fv = _fv(regime="high_vol_trend",
             news_relevance_weighted_sentiment_15m=0.5, news_count_15m=3)
    sig = predict(fv)
    assert sig.horizon_minutes == 60