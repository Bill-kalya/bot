"""News persistence. Append-only, deduplicated, PIT-queryable.

The only query the rest of the system should ever use is
get_news_available_at(ts), which enforces available_time <= ts. Nothing in
the codebase should query the news_items table directly except this module.
"""
from __future__ import annotations

import sqlite3

from core.clock import from_iso, to_iso
from core.types import NewsItem


def insert(conn: sqlite3.Connection, item: NewsItem) -> bool:
    """Insert if new. Returns True if inserted, False if deduplicated."""
    cur = conn.execute(
        """INSERT OR IGNORE INTO news_items(
            news_id, source, source_item_id, url, title, body,
            event_time, available_time, ingested_at,
            raw_hash, scorer_version, sentiment, relevance, event_type,
            source_reliability, superseded_by
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item.news_id, item.source, item.source_item_id, item.url,
            item.title, item.body,
            to_iso(item.event_time) if item.event_time else None,
            to_iso(item.available_time), to_iso(item.ingested_at),
            item.raw_hash, item.scorer_version, item.sentiment,
            item.relevance, item.event_type, item.source_reliability,
            item.superseded_by,
        ),
    )
    return cur.rowcount > 0


def get_news_available_at(
    conn: sqlite3.Connection, ts_iso: str, limit: int = 200,
    *, symbol_filter: bool = True,
) -> list:
    """Return only news whose available_time <= ts_iso.

    This is the PIT boundary. Nothing should ever read news_items outside
    this function for research or decisions.
    """
    q = """
        SELECT * FROM news_items
        WHERE available_time <= ?
          AND superseded_by IS NULL
    """
    if symbol_filter:
        q += " AND relevance >= 0.3"
    q += " ORDER BY available_time DESC LIMIT ?"
    rows = conn.execute(q, (ts_iso, limit)).fetchall()
    return [_row_to_item(r) for r in rows]


def get_by_available_range(
    conn: sqlite3.Connection, start_iso: str, end_iso: str,
) -> list:
    """For backtesting: all news available within a window."""
    rows = conn.execute(
        """SELECT * FROM news_items
           WHERE available_time >= ? AND available_time < ?
             AND superseded_by IS NULL
           ORDER BY available_time ASC""",
        (start_iso, end_iso),
    ).fetchall()
    return [_row_to_item(r) for r in rows]


def _row_to_item(row) -> NewsItem:
    from core.types import NewsItem
    return NewsItem(
        news_id=row["news_id"],
        source=row["source"],
        source_item_id=row["source_item_id"],
        url=row["url"],
        title=row["title"],
        body=row["body"],
        event_time=from_iso(row["event_time"]) if row["event_time"] else None,
        available_time=from_iso(row["available_time"]),
        ingested_at=from_iso(row["ingested_at"]),
        raw_hash=row["raw_hash"],
        scorer_version=row["scorer_version"],
        sentiment=row["sentiment"],
        relevance=row["relevance"],
        event_type=row["event_type"],
        source_reliability=row["source_reliability"],
        superseded_by=row["superseded_by"],
    )