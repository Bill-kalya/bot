"""RSS-based news collector.

Uses feedparser. No API keys required. Works against any RSS/Atom feed that
includes pubDate. Feeds that omit pubDate are stored, but their available_time
is set to ingestion time by the pipeline, and the item is flagged.

This is deliberately unglamorous. It is a source. It is not the strategy.
"""
from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import UTC, datetime

import feedparser

from data.news.collector import RawNewsItem


class RSSCollector:
    def __init__(
        self,
        source_name: str,
        feed_url: str,
        *,
        source_reliability: float = 0.5,
        user_agent: str = "trading-bot-research/0.2",
    ) -> None:
        self.source = source_name
        self.feed_url = feed_url
        self.source_reliability = source_reliability
        self._ua = user_agent

    def fetch(self) -> Iterable[RawNewsItem]:
        parsed = feedparser.parse(
            self.feed_url,
            agent=self._ua,
            request_headers={"Cache-Control": "no-cache"},
        )
        for entry in parsed.entries:
            raw = repr(entry).encode("utf-8", errors="replace")
            source_item_id = (
                entry.get("id")
                or entry.get("guid")
                or hashlib.sha256(raw).hexdigest()
            )
            pub = _parse_feed_time(entry)
            yield RawNewsItem(
                source=self.source,
                source_item_id=str(source_item_id),
                url=str(entry.get("link") or ""),
                title=str(entry.get("title") or "").strip(),
                body=str(entry.get("summary") or entry.get("description") or "").strip(),
                publication_time=pub,
                event_time=None,
                raw_payload=raw,
            )


def _parse_feed_time(entry) -> datetime | None:
    """feedparser normalizes pubDate into published_parsed when it can."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6], tzinfo=UTC)
            except (ValueError, TypeError, OverflowError):
                continue
    return None