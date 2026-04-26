# PROJECT REQUIREMENTS

## 1. Bối cảnh

Shop bán hàng trên Shopee và TikTok Shop cần quay video quá trình đóng hàng để lưu bằng chứng đóng gói, đối chiếu khi có khiếu nại, thiếu hàng, nhầm hàng hoặc tranh chấp.

Hiện tại shop có khoảng 200 đơn/ngày.

Thiết bị quay là điện thoại kết nối với máy tính qua iVCAM. Trên máy tính, iVCAM xuất hiện như một webcam.

## 2. Mục tiêu nghiệp vụ

Hệ thống phải tự động hóa việc quay video theo từng đơn hàng:

- Mỗi mã đơn tương ứng với một video riêng.
- Người dùng chỉ cần đưa QR của đơn hàng vào vùng camera.
- Hệ thống tự bắt đầu quay khi nhận ra QR đơn hàng.
- Khi đưa QR đơn hàng tiếp theo vào, hệ thống tự dừng video đơn hiện tại và bắt đầu video đơn mới.
- Không cần nhân viên thao tác trên máy tính trong lúc đóng hàng.
- Chỉ dùng một QR lệnh duy nhất để kết thúc ca: `CMD:END_SHIFT`.
- Sau khi kết thúc ca, nếu đưa QR đơn hàng mới vào thì hệ thống tự bắt đầu chuỗi quay mới.

## 3. Nền tảng đơn hàng

Hệ thống phục vụ 2 nền tảng:

- Shopee
- TikTok Shop

QR có thể chứa mã đơn trực tiếp hoặc chuỗi có chứa mã đơn. Phiên bản đầu có thể lưu platform là `unknown` nếu chưa xác định được nền tảng.

## 4. Yêu cầu lưu trữ

- Video lưu local trên máy tính.
- Video raw được lưu tạm trong thư mục `raw`.
- Video sau nén được lưu trong thư mục `videos`.
- Sau khi nén thành công, tự xóa file raw.
- Nếu nén lỗi, giữ lại raw và ghi lỗi vào database/log.

## 5. Yêu cầu hiệu năng

Với khoảng 200 đơn/ngày:

- Không được để quá trình nén làm giật hoặc dừng quá trình quay đơn tiếp theo.
- Nén video phải chạy nền bằng queue/worker.
- Ghi video và nhận diện QR phải ưu tiên ổn định hơn chất lượng quá cao.

Thông số đề xuất:

- Độ phân giải: 1280x720
- FPS: 15 hoặc 20
- Video nén: H.264
- CRF: 28
- Preset FFmpeg: veryfast
- Không cần âm thanh ở MVP

## 6. Yêu cầu giao diện

Web local chạy trên trình duyệt, ví dụ:

```text
http://localhost:8000
```

Giao diện cần có:

- Live camera preview.
- Mã đơn đang quay.
- Trạng thái hệ thống.
- Thời lượng video hiện tại.
- Số video đang chờ nén.
- Số video hoàn tất hôm nay.
- Danh sách video gần đây.
- Tìm video theo mã đơn/ngày/nền tảng/trạng thái.
- Nút mở thư mục video.
- Nút dừng khẩn cấp trên web, dành cho quản lý, không thay thế QR `CMD:END_SHIFT`.

## 7. Ràng buộc quan trọng

- Không tự ý thêm nhiều QR lệnh điều khiển như STOP, PAUSE, RESUME, LOCK, UNLOCK.
- QR lệnh duy nhất được phép dùng trong workflow chính là `CMD:END_SHIFT`.
- Không tự ý yêu cầu nhân viên phải bấm máy tính để kết thúc ca.
- Không tự ý chuyển sang cloud storage.
- Không tự ý đổi từ web local sang desktop app.
- Không tự ý giữ raw sau khi nén thành công.
- Không tự ý thay đổi luồng: QR đơn mới sẽ cắt video đơn cũ và quay video mới ngay.
