"""News data package exports."""
from data.news.collector import NewsCollector, RawNewsItem
from data.news.pipeline import canonical_id, ingest, process_one, raw_hash
from data.news.rss_collector import RSSCollector
from data.news.scorer import SCORER_VERSION, ScoredNews, score

__all__ = [
    "SCORER_VERSION",
    "NewsCollector",
    "RSSCollector",
    "RawNewsItem",
    "ScoredNews",
    "canonical_id",
    "ingest",
    "process_one",
    "raw_hash",
    "score",
]