# DATABASE SCHEMA

Database: SQLite

File mặc định:

```text
data/database/packing_video.db
```

## 1. Bảng `order_videos`

```sql
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
```

## 2. Trạng thái `status`

```text
recording   : Đang quay.
queued      : Đã quay xong, chờ nén.
compressing : Đang nén.
done        : Hoàn tất.
failed      : Lỗi.
```

## 3. Trạng thái `compression_status`

```text
pending     : Chưa nén.
compressing : Đang nén.
done        : Nén thành công.
failed      : Nén lỗi.
```

## 4. Bảng `system_events`

Ghi log sự kiện quan trọng.

```sql
CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL
);
```

Event type ví dụ:

```text
camera_started
camera_error
order_started
order_stopped
end_shift_detected
compression_started
compression_done
compression_failed
raw_deleted
raw_delete_failed
disk_space_low
recording_recovered_failed
```

## 5. Bảng `app_state`

Lưu trạng thái hệ thống nếu app restart.

```sql
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Key ví dụ:

```text
current_state
current_session_id
last_order_code
```

## 6. Index đề xuất

```sql
CREATE INDEX IF NOT EXISTS idx_order_videos_order_code ON order_videos(order_code);
CREATE INDEX IF NOT EXISTS idx_order_videos_start_time ON order_videos(start_time);
CREATE INDEX IF NOT EXISTS idx_order_videos_status ON order_videos(status);
CREATE INDEX IF NOT EXISTS idx_order_videos_platform ON order_videos(platform);
```
