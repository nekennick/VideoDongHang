# API SPEC

Backend local: FastAPI

Base URL:

```text
http://localhost:8000
```

## 1. `GET /`

Trả về giao diện web local.

## 2. `GET /api/status`

Trả về trạng thái hiện tại.

Response ví dụ:

```json
{
  "state": "RECORDING",
  "current_order_code": "250426ABC123",
  "current_platform": "shopee",
  "current_duration_seconds": 42.5,
  "compression_queue_size": 3,
  "done_today": 128,
  "failed_today": 0,
  "disk_free_gb": 325.4,
  "camera_connected": true
}
```

## 3. `GET /api/videos`

Query params:

```text
order_code optional
platform optional
status optional
date optional, format YYYY-MM-DD
limit optional, default 50
```

Response:

```json
{
  "items": [
    {
      "id": 1,
      "order_code": "250426ABC123",
      "platform": "shopee",
      "start_time": "2026-04-26T08:12:00+07:00",
      "end_time": "2026-04-26T08:13:12+07:00",
      "duration_seconds": 72,
      "status": "done",
      "video_path": "data/videos/2026-04-26/SHOPEE_250426ABC123.mp4",
      "compressed_size_mb": 8.2
    }
  ]
}
```

## 4. `GET /api/videos/{id}`

Trả metadata video.

## 5. `GET /video/{id}`

Stream file video nén để xem trên trình duyệt.

Chỉ stream khi video đã nén xong và status = done.

## 6. `GET /api/preview.mjpg`

MJPEG stream preview camera.

## 7. `POST /api/admin/emergency-stop`

Nút dừng khẩn cấp cho quản lý trên web.

Lưu ý:

- Đây là chức năng phụ.
- Workflow chính vẫn dùng QR `CMD:END_SHIFT`.
- Không được biến chức năng này thành bước bắt buộc.

Behavior:

```text
Nếu đang quay:
    dừng video hiện tại
    đưa vào queue nén
    chuyển state = SHIFT_ENDED
Nếu không quay:
    chuyển state = SHIFT_ENDED
```

## 8. `POST /api/admin/retry-compression/{id}`

Thử nén lại video bị lỗi.

## 9. `GET /api/config`

Trả cấu hình hiện tại, chỉ những thông tin không nhạy cảm.

## 10. `POST /api/config`

Cho phép cập nhật cấu hình cơ bản như:

- camera_index
- fps
- resolution
- crf
- storage_path

Không được cho phép đổi workflow bắt buộc từ API này.
