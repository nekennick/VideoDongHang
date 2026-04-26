from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from app.utils.time import iso_now, today_text


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.lock = threading.RLock()

    def create_video(self, *, session_id: str, platform: str, order_code: str, qr_content: str, raw_path: str) -> int:
        now = iso_now()
        with self.lock:
            cur = self.conn.execute(
                """
                INSERT INTO order_videos (
                    session_id, platform, order_code, qr_content, raw_path, start_time,
                    status, compression_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'recording', 'pending', ?, ?)
                """,
                (session_id, platform, order_code, qr_content, raw_path, now, now, now),
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def finish_recording(self, video_id: int, duration_seconds: float, raw_size_mb: float | None) -> None:
        now = iso_now()
        with self.lock:
            self.conn.execute(
                """
                UPDATE order_videos
                SET end_time = ?, duration_seconds = ?, status = 'queued',
                    compression_status = 'pending', raw_size_mb = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, duration_seconds, raw_size_mb, now, video_id),
            )
            self.conn.commit()

    def mark_compressing(self, video_id: int) -> None:
        now = iso_now()
        with self.lock:
            self.conn.execute(
                "UPDATE order_videos SET status = 'compressing', compression_status = 'compressing', updated_at = ? WHERE id = ?",
                (now, video_id),
            )
            self.conn.commit()

    def mark_done(self, video_id: int, video_path: str, compressed_size_mb: float, deleted_raw: bool) -> None:
        now = iso_now()
        with self.lock:
            self.conn.execute(
                """
                UPDATE order_videos
                SET status = 'done', compression_status = 'done', video_path = ?,
                    compressed_size_mb = ?, deleted_raw = ?, updated_at = ?, error_message = NULL
                WHERE id = ?
                """,
                (video_path, compressed_size_mb, 1 if deleted_raw else 0, now, video_id),
            )
            self.conn.commit()

    def mark_failed(self, video_id: int, message: str) -> None:
        now = iso_now()
        with self.lock:
            self.conn.execute(
                """
                UPDATE order_videos
                SET status = 'failed', compression_status = 'failed', error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (message, now, video_id),
            )
            self.conn.commit()

    def mark_queued(self, video_id: int) -> None:
        now = iso_now()
        with self.lock:
            self.conn.execute(
                """
                UPDATE order_videos
                SET status = 'queued', compression_status = 'pending', error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (now, video_id),
            )
            self.conn.commit()

    def get_video(self, video_id: int) -> dict[str, Any] | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM order_videos WHERE id = ?", (video_id,)).fetchone()
            return _row_to_dict(row)

    def delete_video(self, video_id: int) -> None:
        with self.lock:
            self.conn.execute("DELETE FROM order_videos WHERE id = ?", (video_id,))
            self.conn.commit()

    def order_code_exists(self, order_code: str) -> bool:
        with self.lock:
            row = self.conn.execute(
                "SELECT 1 FROM order_videos WHERE order_code = ? LIMIT 1",
                (order_code,),
            ).fetchone()
            return row is not None

    def list_videos(
        self,
        *,
        order_code: str | None = None,
        platform: str | None = None,
        status: str | None = None,
        date: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if order_code:
            clauses.append("order_code LIKE ?")
            params.append(f"%{order_code}%")
        if platform:
            clauses.append("platform = ?")
            params.append(platform)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if date:
            clauses.append("substr(start_time, 1, 10) = ?")
            params.append(date)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 200)))
        with self.lock:
            rows = self.conn.execute(
                f"SELECT * FROM order_videos {where} ORDER BY start_time DESC, id DESC LIMIT ?",
                params,
            ).fetchall()
            return [dict(row) for row in rows]

    def count_done_today(self) -> int:
        with self.lock:
            row = self.conn.execute(
                "SELECT COUNT(*) AS c FROM order_videos WHERE status = 'done' AND substr(start_time, 1, 10) = ?",
                (today_text(),),
            ).fetchone()
            return int(row["c"])

    def count_failed_today(self) -> int:
        with self.lock:
            row = self.conn.execute(
                "SELECT COUNT(*) AS c FROM order_videos WHERE status = 'failed' AND substr(start_time, 1, 10) = ?",
                (today_text(),),
            ).fetchone()
            return int(row["c"])

    def pending_compression(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT * FROM order_videos WHERE status IN ('queued', 'compressing') AND raw_path IS NOT NULL ORDER BY id ASC"
            ).fetchall()
            return [dict(row) for row in rows]

    def unfinished_recordings(self) -> list[dict[str, Any]]:
        with self.lock:
            rows = self.conn.execute("SELECT * FROM order_videos WHERE status = 'recording' ORDER BY id ASC").fetchall()
            return [dict(row) for row in rows]

    def log_event(self, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO system_events (event_type, message, metadata_json, created_at) VALUES (?, ?, ?, ?)",
                (event_type, message, json.dumps(metadata or {}, ensure_ascii=False), iso_now()),
            )
            self.conn.commit()

    def set_state(self, key: str, value: str) -> None:
        now = iso_now()
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO app_state (key, value, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            self.conn.commit()

    def get_state(self, key: str) -> str | None:
        with self.lock:
            row = self.conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
            return str(row["value"]) if row is not None else None

    def file_size_mb(self, path: str | None) -> float | None:
        if not path:
            return None
        p = Path(path)
        if not p.exists():
            return None
        return round(p.stat().st_size / (1024 * 1024), 2)
