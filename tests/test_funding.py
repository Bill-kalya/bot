from config import Config
from exchange.fake_adapter import FakeExchange, default_fake_meta
from execution.funding import apply_funding
from storage.db import connect, init_schema
from storage.ledger import Ledger


def _cfg(tmp_path):
    return Config(
        model_version="t", feature_version="t", config_version="t",
        symbol="BTC/USDT:USDT", demo=True, exchange_id="binanceusdm",
        start_equity=10.0, ledger_path=tmp_path / "l.sqlite",
        max_leverage=20, max_loss_per_trade_pct=0.20, daily_loss_cap_pct=0.30,
        min_confidence=0.3, min_edge=0.0005,
        slippage_reserve=0.0005, funding_reserve=0.0002,
        latency_reserve=0.0002, stop_slippage_reserve=0.001,
        loop_seconds=1, candle_limit=60,
        stop_file=tmp_path / "STOP", state_dir=tmp_path,
        reconcile_every_loops=20, funding_lookback_hours=24,
        label_every_loops=40,
        news_feeds=[], news_poll_seconds=300,
        strategy_name="momentum", news_lookback_minutes=120,
        shadow_mode=True,
        paper_only=True,
    )


def test_funding_debits_equity_and_advances_cursor(tmp_path):
    cfg = _cfg(tmp_path)
    conn = connect(cfg.ledger_path)
    init_schema(conn)
    ledger = Ledger(conn, start_equity=cfg.start_equity)

    ex = FakeExchange(default_fake_meta())
    ex.load_markets()

    paid = apply_funding(ex, cfg, ledger, conn)
    assert paid > 0, "fake funding should produce at least one payment"
    assert ledger.equity < 10.0
    assert ledger.get_cursor(f"funding:{cfg.symbol}") is not None


def test_funding_is_idempotent_across_calls(tmp_path):
    cfg = _cfg(tmp_path)
    conn = connect(cfg.ledger_path)
    init_schema(conn)
    ledger = Ledger(conn, start_equity=cfg.start_equity)

    ex = FakeExchange(default_fake_meta())
    ex.load_markets()

    apply_funding(ex, cfg, ledger, conn)
    equity_after_first = ledger.equity

    apply_funding(ex, cfg, ledger, conn)
    assert ledger.equity == equity_after_first, "second call must not double-debit"


def test_funding_fetch_failure_is_not_fatal(tmp_path, monkeypatch):
    cfg = _cfg(tmp_path)
    conn = connect(cfg.ledger_path)
    init_schema(conn)
    ledger = Ledger(conn, start_equity=cfg.start_equity)

    ex = FakeExchange(default_fake_meta())
    ex.load_markets()

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(ex, "fetch_funding_history", boom)
    paid = apply_funding(ex, cfg, ledger, conn)
    assert paid == 0.0
    assert ledger.equity == 10.0