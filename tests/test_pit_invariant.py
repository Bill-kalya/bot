from datetime import UTC, datetime, timedelta

from core.clock import to_iso
from core.types import NewsItem
from storage import news as news_store
from storage.db import connect, init_schema


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


def _item(news_id, available, *, superseded=None, relevance=0.9):
    return NewsItem(
        news_id=news_id, source="test", source_item_id=news_id,
        url="http://x", title="t", body="b",
        event_time=None, available_time=available, ingested_at=available,
        raw_hash="h", scorer_version="v", sentiment=0.1, relevance=relevance,
        event_type="other", source_reliability=0.5, superseded_by=superseded,
    )


def test_query_never_returns_future_news(tmp_path):
    conn = _conn(tmp_path)
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    news_store.insert(conn, _item("a", t0 + timedelta(minutes=1)))
    news_store.insert(conn, _item("b", t0 - timedelta(minutes=1)))

    at_t0 = news_store.get_news_available_at(conn, to_iso(t0))
    ids = {i.news_id for i in at_t0}
    assert ids == {"b"}, "news not yet available must not leak into queries"


def test_query_orders_by_available_time_desc(tmp_path):
    conn = _conn(tmp_path)
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    news_store.insert(conn, _item("old", t0 - timedelta(minutes=30)))
    news_store.insert(conn, _item("new", t0 - timedelta(minutes=5)))

    at_t0 = news_store.get_news_available_at(conn, to_iso(t0))
    assert [i.news_id for i in at_t0] == ["new", "old"]


def test_superseded_records_are_hidden(tmp_path):
    conn = _conn(tmp_path)
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    news_store.insert(conn, _item("a", t0, superseded="b"))
    news_store.insert(conn, _item("b", t0))

    at_t0 = news_store.get_news_available_at(conn, to_iso(t0))
    assert {i.news_id for i in at_t0} == {"b"}