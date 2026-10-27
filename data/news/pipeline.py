"""News pipeline.

Turns RawNewsItem into a stored NewsItem.

Rules:
  - available_time = publication_time if present, else ingested_at.
  - Never set available_time earlier than what we can prove.
  - Compute canonical news_id from (source, source_item_id).
  - Insert with dedup; report whether the item was new.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3

from core.clock import now_utc
from core.types import NewsItem
from data.news import scorer
from data.news.collector import NewsCollector, RawNewsItem
from storage import news as news_store

log = logging.getLogger(__name__)


def canonical_id(source: str, source_item_id: str) -> str:
    return hashlib.sha256(f"{source}::{source_item_id}".encode()).hexdigest()


def raw_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def process_one(
    conn: sqlite3.Connection, raw: RawNewsItem, source_reliability: float,
) -> bool:
    """Insert one item. Returns True if newly stored."""
    ingested = now_utc()

    # PIT boundary rule.
    available = raw.publication_time or ingested
    available = min(available, ingested)

    scored = scorer.score(raw.title, raw.body)
    item = NewsItem(
        news_id=canonical_id(raw.source, raw.source_item_id),
        source=raw.source,
        source_item_id=raw.source_item_id,
        url=raw.url,
        title=raw.title,
        body=raw.body,
        event_time=raw.event_time,
        available_time=available,
        ingested_at=ingested,
        raw_hash=raw_hash(raw.raw_payload),
        scorer_version=scored.scorer_version,
        sentiment=scored.sentiment,
        relevance=scored.relevance,
        event_type=scored.event_type,
        source_reliability=source_reliability,
        superseded_by=None,
    )
    return news_store.insert(conn, item)


def ingest(
    conn: sqlite3.Connection, collector: NewsCollector
) -> dict:
    """Fetch from a collector and store. Returns counts."""
    inserted = 0
    seen = 0
    try:
        for raw in collector.fetch():
            seen += 1
            if process_one(conn, raw, collector.source_reliability):
                inserted += 1
    except Exception as e:
        log.exception("collector %s failed", collector.source)
        return {"source": collector.source, "seen": seen,
                "inserted": inserted, "error": str(e)}
    return {"source": collector.source, "seen": seen,
            "inserted": inserted, "error": None}