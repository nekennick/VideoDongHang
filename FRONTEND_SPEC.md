# FRONTEND SPEC

## 1. Mục tiêu giao diện

Giao diện web local đơn giản, chạy trên trình duyệt, ưu tiên rõ ràng và ổn định.

URL mặc định:

```text
http://localhost:8000
```

## 2. Màn hình chính

Cần hiển thị:

- Live camera preview.
- Trạng thái hệ thống:
  - IDLE
  - RECORDING
  - SHIFT_ENDED
  - ERROR
- Mã đơn đang quay.
- Nền tảng hiện tại: Shopee/TikTok/Unknown.
- Thời lượng video hiện tại.
- Số video trong queue nén.
- Số video hoàn tất hôm nay.
- Dung lượng ổ còn trống.
- Cảnh báo nếu camera mất kết nối.
- Cảnh báo nếu ổ cứng sắp đầy.

## 3. Vùng QR trên preview

Nếu bật ROI, preview nên vẽ khung vùng đọc QR.

Mục tiêu để nhân viên biết cần đưa QR vào đâu.

## 4. Danh sách video gần đây

Hiển thị 20-50 video gần nhất:

- Thời gian
- Mã đơn
- Nền tảng
- Trạng thái
- Thời lượng
- Dung lượng
- Nút xem video nếu done

## 5. Tìm kiếm video

Bộ lọc:

- Mã đơn
- Ngày
- Nền tảng
- Trạng thái

Kết quả có:

- Xem video
- Copy đường dẫn
- Mở thư mục chứa video nếu có thể hỗ trợ trên Windows

## 6. Nút quản trị

Có thể có nút:

```text
Dừng khẩn cấp / Kết thúc ca
```

Lưu ý:

- Đây là phương án phụ cho quản lý.
- Không thay thế workflow QR `CMD:END_SHIFT`.
- Không yêu cầu nhân viên phải dùng nút này.

## 7. Màu trạng thái gợi ý

- IDLE: xám/xanh nhạt
- RECORDING: đỏ
- SHIFT_ENDED: vàng/xanh
- ERROR: đỏ đậm

## 8. Refresh dữ liệu

Frontend gọi `/api/status` mỗi 1 giây.

Danh sách video có thể refresh mỗi 3-5 giây hoặc khi có event mới.
