from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {"storage/news.py", "storage/db.py", "check_db.py", "scripts/run_experiments.py", "research/labeler.py"}
NEEDLE = "news_items"


def test_only_storage_news_touches_news_items_table():
    offenders = []
    for path in ROOT.rglob("*.py"):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel in ALLOWED or rel.startswith("tests/"):
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if NEEDLE in text:
            offenders.append(rel)
    assert not offenders, (
        f"modules must use storage.news API, not the news_items table: {offenders}"
    )