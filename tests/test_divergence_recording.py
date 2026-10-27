from execution.divergence import record_entry_divergence, record_exit_divergence
from storage.db import connect, init_schema


def _conn(tmp_path):
    c = connect(tmp_path / "l.sqlite")
    init_schema(c)
    return c


def test_entry_divergence_is_recorded(tmp_path):
    conn = _conn(tmp_path)
    record_entry_divergence(
        conn, prediction_id="p1", paper_price=60_010.0, demo_price=60_000.0,
        paper_fee=0.03, demo_fee=0.03, demo_latency_ms=120,
    )
    row = conn.execute("SELECT * FROM divergences").fetchone()
    assert row["kind"] == "entry"
    assert abs(row["price_diff_pct"] - (10.0 / 60_000.0)) < 1e-9


def test_exit_divergence_is_recorded(tmp_path):
    conn = _conn(tmp_path)
    record_exit_divergence(
        conn, prediction_id="p1", paper_price=59_990.0, demo_price=60_000.0,
        paper_fee=0.03, demo_fee=0.03, reason="stop",
    )
    row = conn.execute("SELECT * FROM divergences").fetchone()
    assert row["kind"] == "exit"
    assert row["notes"] == "stop"