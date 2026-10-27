import pytest

from core.errors import Halt
from exchange.fake_adapter import FakeExchange, default_fake_meta
from execution.stops import place_protective_stop


def _ex() -> FakeExchange:
    ex = FakeExchange(default_fake_meta())
    ex.load_markets()
    return ex


def test_place_stop_returns_live_order() -> None:
    ex = _ex()
    stop = place_protective_stop(ex, "BTC/USDT:USDT", "long", 0.001, 59_000.0)
    assert stop["status"] == "open"
    assert stop["reduceOnly"] is True


def test_place_stop_rejects_when_exchange_raises(monkeypatch) -> None:
    ex = _ex()

    def boom(*a, **k):
        raise RuntimeError("exchange down")

    monkeypatch.setattr(ex, "create_stop_market", boom)
    with pytest.raises(Halt):
        place_protective_stop(ex, "BTC/USDT:USDT", "long", 0.001, 59_000.0)


def test_place_stop_rejects_when_not_live(monkeypatch) -> None:
    ex = _ex()
    original = ex.create_stop_market

    def silent(*a, **k):
        order = original(*a, **k)
        order["status"] = "canceled"
        return order

    monkeypatch.setattr(ex, "create_stop_market", silent)
    with pytest.raises(Halt):
        place_protective_stop(ex, "BTC/USDT:USDT", "long", 0.001, 59_000.0)