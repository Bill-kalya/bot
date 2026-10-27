"""Sentiment and relevance scoring.

Scorer output is versioned. When the scorer changes, we do not edit existing
rows. We re-score and write new rows with a new scorer_version, and mark the
old ones as superseded.

The baseline scorer is deliberately simple: keyword counting. It is not
expected to be good. It is expected to be *honest* and *deterministic*, so
that when a learned model replaces it, we can measure the improvement against
a known reference.
"""
from __future__ import annotations

from dataclasses import dataclass

SCORER_VERSION = "keyword-v0.2.0"

# Deliberately tiny lexicons. These are the seed; expansion is a research task.
_BULLISH = {
    "approval", "approved", "adoption", "inflow", "etf", "buy", "bought",
    "rally", "surge", "gain", "bullish", "upgrade", "partnership", "launch",
    "halving", "institutional", "reserve",
}
_BEARISH = {
    "ban", "banned", "hack", "exploit", "outflow", "sell", "sold", "crash",
    "drop", "plunge", "bearish", "downgrade", "lawsuit", "sec charges",
    "fraud", "liquidation", "delisting",
}
_RELEVANCE_TERMS = {
    "bitcoin", "btc", "crypto", "cryptocurrency", "blockchain", "binance",
    "coinbase", "etf", "stablecoin", "defi", "altcoin",
}


@dataclass(frozen=True)
class ScoredNews:
    sentiment: float    # -1..1
    relevance: float    # 0..1
    event_type: str     # "regulation", "listing", "macro", "other"
    scorer_version: str


def score(title: str, body: str) -> ScoredNews:
    text = f"{title} {body}".lower()
    words = _tokenize(text)
    word_set = set(words)

    bull = len(word_set & _BULLISH)
    bear = len(word_set & _BEARISH)
    raw = bull - bear
    # Normalize by sqrt of total hits; small counts stay small.
    sentiment = 0.0 if raw == 0 else max(-1.0, min(1.0, raw / (abs(raw) + 3)))

    rel_hits = len(word_set & _RELEVANCE_TERMS)
    relevance = min(1.0, rel_hits / 3.0)

    event_type = _classify(text)

    return ScoredNews(
        sentiment=sentiment,
        relevance=relevance,
        event_type=event_type,
        scorer_version=SCORER_VERSION,
    )


def _tokenize(text: str) -> list[str]:
    out = []
    cur = []
    for ch in text:
        if ch.isalnum():
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


def _classify(text: str) -> str:
    if any(k in text for k in ("sec", "regulat", "lawsuit", "ban", "approved etf")):
        return "regulation"
    if any(k in text for k in ("listing", "listed", "delist")):
        return "listing"
    if any(k in text for k in ("fed", "inflation", "cpi", "rate", "macro")):
        return "macro"
    return "other"