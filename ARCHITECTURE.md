# ARCHITECTURE

## 1. Tổng quan

```text
Phone Camera
   ↓ iVCAM
Windows Webcam Device
   ↓ OpenCV Capture Thread
QR Scanner + Frame Dispatcher
   ↓
Recording Session Manager
   ↓
Raw Video Writer
   ↓ stop current order
Compression Queue
   ↓ FFmpeg Worker
Compressed Videos Folder
   ↓
SQLite Metadata Database
   ↓
FastAPI Local Web UI/API
```

## 2. Thành phần chính

### 2.1 Camera Service

Nhiệm vụ:

- Mở camera iVCAM qua OpenCV.
- Đọc frame liên tục.
- Cung cấp frame cho:
  - QR detector.
  - Video writer nếu đang quay.
  - Live preview web.

### 2.2 QR Detector

Nhiệm vụ:

- Đọc QR từ frame.
- Phân loại QR:
  - QR đơn hàng.
  - QR lệnh `CMD:END_SHIFT`.
  - QR không hợp lệ.

### 2.3 Recording Session Manager

Nhiệm vụ:

- Quản lý trạng thái IDLE/RECORDING/SHIFT_ENDED/ERROR.
- Tạo file raw cho từng đơn.
- Dừng video hiện tại khi có đơn mới hoặc kết thúc ca.
- Đưa file raw đã hoàn tất vào compression queue.

### 2.4 Compression Worker

Nhiệm vụ:

- Nhận job từ queue.
- Gọi FFmpeg để nén video.
- Nếu nén thành công:
  - Cập nhật database.
  - Xóa raw.
- Nếu nén lỗi:
  - Giữ raw.
  - Cập nhật trạng thái failed.
  - Ghi log.

### 2.5 SQLite Repository

Nhiệm vụ:

- Lưu metadata video.
- Lưu trạng thái nén.
- Hỗ trợ tìm kiếm video theo mã đơn, ngày, nền tảng, trạng thái.

### 2.6 FastAPI Web Server

Nhiệm vụ:

- Phục vụ web local.
- Cung cấp API trạng thái hệ thống.
- Cung cấp stream preview camera.
- Cung cấp danh sách video.
- Cho phép xem video nén.
- Cho phép thao tác quản trị như dừng khẩn cấp.

## 3. Luồng dữ liệu chính

### Khi thấy QR đơn mới

```text
QR Detector
→ Recording Session Manager
→ stop_current_recording()
→ enqueue_compression(raw_file)
→ start_new_recording(order_code)
```

### Khi thấy CMD:END_SHIFT

```text
QR Detector
→ End Shift debounce 1 second
→ Recording Session Manager.end_shift()
→ stop_current_recording()
→ enqueue_compression(raw_file)
→ state = SHIFT_ENDED
```

### Khi nén xong

```text
Compression Worker
→ ffmpeg compress raw to videos folder
→ verify output exists and size > 0
→ update SQLite status = done
→ delete raw
```

## 4. Đề xuất cấu trúc source code

```text
packing-video-system/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── camera/
│   │   ├── capture.py
│   │   ├── qr_detector.py
│   │   └── frame_buffer.py
│   ├── recording/
│   │   ├── session_manager.py
│   │   ├── video_writer.py
│   │   └── order_parser.py
│   ├── compression/
│   │   ├── queue.py
│   │   └── ffmpeg_worker.py
│   ├── db/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── web/
│   │   ├── routes.py
│   │   ├── api.py
│   │   └── static/
│   │       ├── index.html
│   │       ├── app.js
│   │       └── style.css
│   └── utils/
│       ├── logging.py
│       ├── paths.py
│       └── time.py
│
├── data/
│   ├── raw/
│   ├── videos/
│   ├── database/
│   └── logs/
│
├── config.json
├── requirements.txt
├── run.bat
└── README.md
```
