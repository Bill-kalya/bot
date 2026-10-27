import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
FORBIDDEN = [
    (re.compile(r"\b50\.0\b"), "possible hard-coded min_notional"),
    (re.compile(r"\b0\.0005\b"), "possible hard-coded taker fee"),
]

ALLOWED_FILES = {
    "exchange/fake_adapter.py",   # explicit, labelled test-only metadata
    "exchange/ccxt_adapter.py",   # comment explaining we DON'T hardcode 0.0005
    "research/backtester.py",     # fallback defaults when exchange unavailable
    "data/features.py",           # RSI neutral value 50.0, not min_notional
    "tests/",
    ".env.example",
    "config.py",                  # env defaults for cost reserves, not market facts
    "main.py",                    # local cost estimates, not exchange facts
    "core/types.py",              # docstring examples only
    "phase9.py",                  # synthetic data generation (0.0005 = 5bps volatility)
}

EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def test_no_hardcoded_market_facts_in_src() -> None:
    hits = []
    for path in SRC.rglob("*.py"):
        # Skip excluded directories
        if any(excl in path.parts for excl in EXCLUDE_DIRS):
            continue
        rel = str(path.relative_to(SRC)).replace("\\", "/")
        if any(a in rel for a in ALLOWED_FILES):
            continue
        text = path.read_text()
        for pat, why in FORBIDDEN:
            if pat.search(text):
                hits.append(f"{rel}: {why} -> {pat.pattern}")
    assert not hits, "hard-coded market facts found:\n" + "\n".join(hits)