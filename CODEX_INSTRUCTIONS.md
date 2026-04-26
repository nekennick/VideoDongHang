# CODEX INSTRUCTIONS - ĐỌC TRƯỚC KHI CODE

Bạn là Codex/dev triển khai dự án Packing Video System.

## 1. Mục tiêu không được làm sai

Xây dựng web local chạy trên máy Windows để quay video đóng hàng bằng điện thoại qua iVCAM.

Workflow bắt buộc:

```text
QR đơn đầu tiên → bắt đầu quay ngay
QR đơn mới → dừng video đơn hiện tại, bắt đầu video đơn mới ngay
CMD:END_SHIFT → kết thúc ca, dừng chuỗi quay
Sau SHIFT_ENDED, QR đơn mới → tự bắt đầu chuỗi mới
```

## 2. Chỉ có một QR lệnh

QR lệnh duy nhất:

```text
CMD:END_SHIFT
```

Không tự ý thêm:

```text
CMD:STOP
CMD:PAUSE
CMD:RESUME
CMD:LOCK
CMD:UNLOCK
```

Muốn thêm phải hỏi chủ dự án.

## 3. Không tự ý đổi nền tảng

Đã chốt:

- Web local trên trình duyệt.
- Backend Python FastAPI.
- OpenCV nhận camera và đọc QR.
- FFmpeg nén video.
- SQLite lưu metadata.
- Video lưu local.

Không tự ý chuyển sang desktop app, cloud app, mobile app hoặc server cloud.

## 4. Raw video

Raw video là file tạm.

Bắt buộc:

```text
Nén thành công → xóa raw
Nén lỗi → giữ raw
```

Không tự ý giữ raw vĩnh viễn.

## 5. Ưu tiên khi code

Ưu tiên theo thứ tự:

1. Workflow đúng.
2. Không mất video.
3. App không crash.
4. Nén chạy nền, không chặn quay.
5. Giao diện đơn giản, dễ dùng.
6. Tối ưu đẹp sau.

## 6. Khi có điểm chưa rõ

Nếu có bất kỳ điểm nào làm khác tài liệu, phải hỏi chủ dự án trước.

Không được tự suy diễn workflow mới.

## 7. Tiêu chuẩn code

- Code rõ ràng, chia module.
- Có logging.
- Có error handling.
- Không hardcode path nếu đã có config.
- Sanitize mã đơn trước khi đặt tên file.
- Không để thread ghi video và thread nén tranh chấp file.
- Không xóa raw trước khi xác nhận file nén tồn tại và dung lượng > 0.

## 8. Tối thiểu cần bàn giao

- Source code chạy được.
- `requirements.txt`.
- `config.json` mẫu.
- `run.bat` cho Windows.
- README hướng dẫn cài FFmpeg, cài Python package và chạy app.
- Database tự tạo.
- Web local xem camera, trạng thái, danh sách video.
