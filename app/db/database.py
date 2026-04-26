from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS order_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'unknown',
    order_code TEXT NOT NULL,
    qr_content TEXT,
    raw_path TEXT,
    video_path TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_seconds REAL,
    status TEXT NOT NULL,
    compression_status TEXT NOT NULL DEFAULT 'pending',
    raw_size_mb REAL,
    compressed_size_mb REAL,
    deleted_raw INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_videos_order_code ON order_videos(order_code);
CREATE INDEX IF NOT EXISTS idx_order_videos_start_time ON order_videos(start_time);
CREATE INDEX IF NOT EXISTS idx_order_videos_status ON order_videos(status);
CREATE INDEX IF NOT EXISTS idx_order_videos_platform ON order_videos(platform);
"""


def db_path(config: dict) -> Path:
    return Path(config["storage"]["database_dir"]) / "packing_video.db"


def connect(config: dict) -> sqlite3.Connection:
    path = db_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(config: dict) -> None:
    with connect(config) as conn:
        conn.executescript(SCHEMA)
        conn.commit()

