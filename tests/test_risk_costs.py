from config import Config
from core.clock import now_utc
from core.types import FeeSchedule, MarketMeta, Signal
from risk.costs import expected_net_trade_return


def _meta(taker: float = 0.0005):
    return MarketMeta(
        symbol="BTC/USDT:USDT",
        min_notional=50.0,
        min_quantity=0.001,
        quantity_step=0.001,
        tick_size=0.1,
        max_leverage=125,
        fees=FeeSchedule(taker=taker, maker=0.0002, fetched_at=now_utc()),
        fetched_at=now_utc(),
    )


def _signal(direction: int = 1, expected: float = 0.01):
    return Signal(
        decision_time=now_utc(),
        symbol="BTC/USDT:USDT",
        horizon_minutes=15,
        direction=direction,
        confidence=0.9,
        expected_signed_return=expected,
        expected_volatility=0.005,
        source_version="test",
    )


def _cfg(tmp_path, **over):
    base = {
        "model_version": "t", "feature_version": "t", "config_version": "t",
        "symbol": "BTC/USDT:USDT", "demo": True, "exchange_id": "binanceusdm",
        "start_equity": 10.0, "ledger_path": tmp_path / "l.sqlite",
        "max_leverage": 20, "max_loss_per_trade_pct": 0.20, "daily_loss_cap_pct": 0.30,
        "min_confidence": 0.3, "min_edge": 0.0005,
        "slippage_reserve": 0.0005, "funding_reserve": 0.0002,
        "latency_reserve": 0.0002, "stop_slippage_reserve": 0.001,
        "loop_seconds": 1, "candle_limit": 60,
        "stop_file": tmp_path / "STOP", "state_dir": tmp_path,
        "reconcile_every_loops": 20, "funding_lookback_hours": 24,
        "label_every_loops": 40,
        "news_feeds": [], "news_poll_seconds": 300,
        "strategy_name": "momentum", "news_lookback_minutes": 120,
        "shadow_mode": True,
        "paper_only": True,
    }
    base.update(over)
    return Config(**base)


def test_long_positive_expected_yields_positive_gross(tmp_path):
    net, _ = expected_net_trade_return(_signal(1, 0.01), _meta(), _cfg(tmp_path))
    assert net > 0


def test_short_negative_expected_yields_positive_gross(tmp_path):
    net, _ = expected_net_trade_return(_signal(-1, -0.01), _meta(), _cfg(tmp_path))
    assert net > 0


def test_short_with_positive_expected_yields_negative(tmp_path):
    net, _ = expected_net_trade_return(_signal(-1, 0.01), _meta(), _cfg(tmp_path))
    assert net < 0


def test_slippage_scales_with_volatility(tmp_path):
    cfg = _cfg(tmp_path)
    calm = _signal(1, 0.01)
    from core.types import Signal
    wild = Signal(
        decision_time=calm.decision_time, symbol=calm.symbol,
        horizon_minutes=calm.horizon_minutes, direction=1, confidence=0.9,
        expected_signed_return=0.01, expected_volatility=0.05,
        source_version="test",
    )
    _, c_calm = expected_net_trade_return(calm, _meta(), cfg)
    _, c_wild = expected_net_trade_return(wild, _meta(), cfg)
    assert c_wild.slippage > c_calm.slippage