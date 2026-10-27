"""SQLite schema + connection. Migrations live as numbered SQL strings."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id TEXT PRIMARY KEY,
  decision_time TEXT NOT NULL,
  symbol TEXT NOT NULL,
  price REAL,
  horizon_minutes INTEGER,
  direction INTEGER,
  confidence REAL,
  expected_signed_return REAL,
  expected_volatility REAL,
  estimated_entry_fee REAL,
  estimated_exit_fee REAL,
  estimated_slippage REAL,
  estimated_funding REAL,
  expected_net_trade_return REAL,
  risk_decision TEXT,
  rejection_reason TEXT,
  model_version TEXT,
  feature_version TEXT,
  config_version TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
  prediction_id TEXT PRIMARY KEY REFERENCES predictions(prediction_id),
  outcome_time TEXT,
  price_15m REAL, return_15m REAL, net_return_15m REAL,
  price_60m REAL, return_60m REAL, net_return_60m REAL
);

CREATE TABLE IF NOT EXISTS outcomes_by_horizon (
  prediction_id TEXT NOT NULL,
  horizon_minutes INTEGER NOT NULL,
  price REAL,
  gross_return REAL,
  net_return REAL,
  PRIMARY KEY (prediction_id, horizon_minutes),
  FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
);

CREATE INDEX IF NOT EXISTS idx_obh_pid ON outcomes_by_horizon(prediction_id);
CREATE INDEX IF NOT EXISTS idx_obh_horizon ON outcomes_by_horizon(horizon_minutes);

CREATE TABLE IF NOT EXISTS trades (
  trade_id TEXT PRIMARY KEY,
  prediction_id TEXT REFERENCES predictions(prediction_id),
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  quantity REAL NOT NULL,
  notional REAL NOT NULL,
  leverage INTEGER NOT NULL,

  opened_at TEXT NOT NULL,
  closed_at TEXT,

  entry_price REAL NOT NULL,
  exit_price REAL,

  stop_price REAL NOT NULL,
  stop_distance_pct REAL NOT NULL,
  target_distance_pct REAL NOT NULL,

  fees_paid REAL NOT NULL DEFAULT 0,
  funding_paid REAL NOT NULL DEFAULT 0,
  realized_pnl REAL,

  close_reason TEXT
);

CREATE TABLE IF NOT EXISTS news_items (
  news_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_item_id TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,

  event_time TEXT,
  available_time TEXT NOT NULL,
  ingested_at TEXT NOT NULL,

  raw_hash TEXT NOT NULL,
  scorer_version TEXT NOT NULL,
  sentiment REAL NOT NULL,
  relevance REAL NOT NULL,
  event_type TEXT NOT NULL,
  source_reliability REAL NOT NULL,
  superseded_by TEXT,

  UNIQUE(source, source_item_id)
);

CREATE TABLE IF NOT EXISTS paper_trades (
  trade_id TEXT PRIMARY KEY,
  prediction_id TEXT REFERENCES predictions(prediction_id),
  side TEXT NOT NULL,
  quantity REAL NOT NULL,
  entry_price REAL NOT NULL,
  entry_ts TEXT NOT NULL,
  stop_price REAL NOT NULL,
  stop_distance_pct REAL NOT NULL,
  target_distance_pct REAL NOT NULL,
  entry_fee REAL NOT NULL DEFAULT 0,
  funding_paid REAL NOT NULL DEFAULT 0,
  equity_before REAL NOT NULL,

  exit_price REAL,
  exit_ts TEXT,
  exit_fee REAL,
  realized_pnl REAL,
  close_reason TEXT,
  equity_after REAL
);

CREATE TABLE IF NOT EXISTS divergences (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prediction_id TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  kind TEXT NOT NULL,             -- entry | exit
  paper_price REAL,
  demo_price REAL,
  price_diff_pct REAL,
  paper_fee REAL,
  demo_fee REAL,
  demo_latency_ms INTEGER,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_time TEXT NOT NULL,
  kind TEXT NOT NULL,
  payload TEXT
);

CREATE INDEX IF NOT EXISTS idx_predictions_time ON predictions(decision_time);
CREATE INDEX IF NOT EXISTS idx_events_time ON events(event_time);
CREATE INDEX IF NOT EXISTS idx_trades_opened ON trades(opened_at);
CREATE INDEX IF NOT EXISTS idx_trades_prediction ON trades(prediction_id);
CREATE INDEX IF NOT EXISTS idx_news_available ON news_items(available_time);
CREATE INDEX IF NOT EXISTS idx_news_source ON news_items(source);
CREATE INDEX IF NOT EXISTS idx_paper_trades_entry ON paper_trades(entry_ts);
CREATE INDEX IF NOT EXISTS idx_paper_trades_prediction ON paper_trades(prediction_id);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit; we manage txns
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def migrate_add_outcomes_by_horizon(conn: sqlite3.Connection) -> None:
    """Idempotent migration. Safe to call on every startup."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outcomes_by_horizon (
          prediction_id TEXT NOT NULL,
          horizon_minutes INTEGER NOT NULL,
          price REAL,
          gross_return REAL,
          net_return REAL,
          PRIMARY KEY (prediction_id, horizon_minutes),
          FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_obh_pid ON outcomes_by_horizon(prediction_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_obh_horizon ON outcomes_by_horizon(horizon_minutes)"
    )


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    migrate_add_outcomes_by_horizon(conn)