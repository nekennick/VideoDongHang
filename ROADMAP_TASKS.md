# ROADMAP TASKS FOR CODEX

## Phase 1 - Skeleton chạy được

1. Tạo project Python FastAPI.
2. Tạo cấu trúc thư mục app/data/config.
3. Tạo `config.json` mẫu.
4. Tạo SQLite init.
5. Tạo web page đơn giản ở `/`.
6. Tạo `/api/status` trả mock status.

Definition of Done:

- Chạy `run.bat` mở được web local.
- SQLite được tạo.
- Config đọc được.

## Phase 2 - Camera preview

1. Mở camera bằng OpenCV.
2. Tạo frame buffer thread-safe.
3. Tạo MJPEG stream `/api/preview.mjpg`.
4. Hiển thị live preview trên web.
5. Hiển thị lỗi nếu không mở được camera.

Definition of Done:

- iVCAM camera hiện trên web.
- App không crash khi camera mất kết nối.

## Phase 3 - QR detection

1. Tích hợp QR detector.
2. Hỗ trợ ROI.
3. Phân loại QR đơn hàng và `CMD:END_SHIFT`.
4. Log QR detect event.
5. Hiển thị QR gần nhất trên web.

Definition of Done:

- Đưa QR vào camera thì web hiện nội dung QR.
- `CMD:END_SHIFT` được nhận diện đúng nhưng chưa cần điều khiển quay ở phase này.

## Phase 4 - Recording session manager

1. Tạo session manager với state IDLE/RECORDING/SHIFT_ENDED/ERROR.
2. Khi thấy QR đơn đầu tiên, bắt đầu quay.
3. Khi thấy QR đơn mới, dừng video cũ và quay video mới.
4. Khi thấy cùng QR đơn hiện tại, bỏ qua.
5. Ghi metadata vào SQLite.

Definition of Done:

- Tạo được nhiều video raw theo nhiều QR đơn khác nhau.
- QR mới tự cắt video cũ.

## Phase 5 - End Shift QR

1. Thêm xử lý `CMD:END_SHIFT`.
2. Debounce 1 giây cho `CMD:END_SHIFT`.
3. Khi end shift, dừng video hiện tại.
4. Chuyển state = SHIFT_ENDED.
5. Khi thấy QR đơn mới sau SHIFT_ENDED, tự quay lại.

Definition of Done:

- Chỉ cần một QR kết thúc ca.
- Không cần bấm nút Start để bắt đầu lại.

## Phase 6 - Compression worker

1. Tạo compression queue.
2. Tạo FFmpeg worker chạy nền.
3. Khi video raw kết thúc, enqueue nén.
4. Nén xong thì xóa raw.
5. Nén lỗi thì giữ raw.
6. Cập nhật SQLite đầy đủ.

Definition of Done:

- Đang nén video cũ vẫn quay được video mới.
- Raw tự xóa sau khi nén thành công.

## Phase 7 - Frontend hoàn chỉnh

1. Hiển thị status realtime.
2. Hiển thị danh sách video gần đây.
3. Tìm kiếm video theo mã đơn/ngày/nền tảng/trạng thái.
4. Xem video trên web.
5. Hiển thị queue nén và dung lượng ổ đĩa.

Definition of Done:

- Dùng được cho quy trình đóng hàng thực tế.

## Phase 8 - Stability

1. Recover job nén dang dở khi app restart.
2. Log file chi tiết.
3. Cảnh báo mất camera.
4. Cảnh báo ổ cứng sắp đầy.
5. Thêm script chạy Windows `run.bat`.

Definition of Done:

- App chịu được lỗi camera/nén/restart ở mức cơ bản.
