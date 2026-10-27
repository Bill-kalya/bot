"""News collectors.

A collector fetches raw items from a source and yields RawNewsItem dicts.
Normalization into NewsItem happens in the pipeline, not here. The collector
is responsible only for fetching and for providing whatever timestamps the
source makes available.

Collectors must never set available_time to something earlier than what the
source actually provided. If the source does not report a publication time,
the collector reports publication_time=None, and the pipeline sets
available_time = ingestion_time.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class RawNewsItem:
    source: str
    source_item_id: str
    url: str
    title: str
    body: str
    publication_time: datetime | None   # what the source claims
    event_time: datetime | None         # source's own event timestamp, if any
    raw_payload: bytes                  # verbatim, for hashing and re-parsing


class NewsCollector(Protocol):
    source: str
    source_reliability: float

    def fetch(self) -> Iterable[RawNewsItem]: ...