"""Strategy registry. One place to add or swap strategies."""
from __future__ import annotations

from collections.abc import Callable

from core.types import FeatureVector, Signal

StrategyFn = Callable[["FeatureVector"], "Signal"]


def get(name: str):
    if name == "momentum":
        from strategy.baseline import predict_features as fn
        return fn
    if name == "news":
        from strategy.news_model import predict
        return predict
    if name == "news_filtered":
        from strategy.news_model_filtered import predict
        return predict
    raise KeyError(f"unknown strategy: {name}")