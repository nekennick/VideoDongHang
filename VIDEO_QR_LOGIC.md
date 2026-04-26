# VIDEO AND QR LOGIC

## 1. Loại QR

Hệ thống chỉ xử lý 2 loại QR:

### 1.1 QR đơn hàng

Là QR chứa mã đơn Shopee hoặc TikTok Shop.

Ví dụ:

```text
250426ABC123
577812345678901
ORDER:250426ABC123
```

### 1.2 QR kết thúc ca

Chính xác:

```text
CMD:END_SHIFT
```

Không thêm STOP/PAUSE/RESUME/LOCK/UNLOCK nếu chưa được chủ dự án duyệt.

## 2. Phân loại QR

Pseudo-code:

```python
def classify_qr(content: str):
    normalized = content.strip()

    if normalized == "CMD:END_SHIFT":
        return {"type": "end_shift"}

    order_code = extract_order_code(normalized)
    if order_code:
        return {
            "type": "order",
            "order_code": order_code,
            "platform": detect_platform(order_code, normalized),
            "raw_content": content,
        }

    return {"type": "invalid"}
```

## 3. Xử lý QR đơn hàng

Pseudo-code bắt buộc:

```python
def handle_order_qr(order_code, platform, raw_content):
    if state in ["IDLE", "SHIFT_ENDED"]:
        start_new_session_if_needed()
        start_recording(order_code, platform, raw_content)
        state = "RECORDING"
        return

    if state == "RECORDING":
        if order_code == current_order_code:
            return

        stop_current_recording()
        enqueue_compression(current_raw_file)
        start_recording(order_code, platform, raw_content)
        return
```

## 4. Xử lý QR `CMD:END_SHIFT`

QR kết thúc ca cần debounce 1 giây.

Pseudo-code:

```python
def handle_end_shift_qr():
    if not seen_continuously_for("CMD:END_SHIFT", seconds=1.0):
        return

    if state == "RECORDING":
        stop_current_recording()
        enqueue_compression(current_raw_file)

    state = "SHIFT_ENDED"
    current_order_code = None
```

## 5. Chống quét lặp

- Cùng QR đơn đang quay: bỏ qua.
- QR đơn mới: xử lý ngay.
- Sau khi chuyển đơn, có thể dùng cooldown cực ngắn 0.2-0.3 giây để tránh cùng frame gây double event.
- Không được làm cooldown dài khiến nhân viên phải chờ lâu.

## 6. Vùng nhận QR

Đề xuất có `qr_roi_enabled` trong config.

Mục tiêu:

- Chỉ đọc QR trong một vùng cố định của frame.
- Tránh camera đọc nhầm QR nằm xa trong khu đóng hàng.

Config ví dụ:

```json
{
  "qr_roi_enabled": true,
  "qr_roi": {
    "x": 0.05,
    "y": 0.05,
    "w": 0.35,
    "h": 0.35
  }
}
```

Tọa độ tính theo tỷ lệ frame.

## 7. Đặt tên file

File raw:

```text
data/raw/YYYY-MM-DD/YYYY-MM-DD_HH-mm-ss_PLATFORM_ORDER_raw.mp4
```

File nén:

```text
data/videos/YYYY-MM-DD/YYYY-MM-DD_HH-mm-ss_PLATFORM_ORDER.mp4
```

Cần sanitize order_code để tránh ký tự lỗi path.
