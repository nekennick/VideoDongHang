# MANDATORY WORKFLOW - KHÔNG ĐƯỢC TỰ Ý THAY ĐỔI

Tài liệu này là workflow bắt buộc. Nếu muốn làm khác bất kỳ điểm nào, phải hỏi chủ dự án trước.

## 1. Workflow bắt đầu ca

Không cần nút Start riêng cho nhân viên.

```text
Camera đang hoạt động
→ hệ thống ở trạng thái IDLE hoặc SHIFT_ENDED
→ nhân viên đưa QR đơn hàng đầu tiên vào camera
→ hệ thống bắt đầu quay video cho đơn đó ngay
```

## 2. Workflow trong ca

```text
Đang quay đơn A
→ camera thấy QR đơn B
→ hệ thống dừng video đơn A
→ đưa video đơn A vào hàng chờ nén
→ bắt đầu quay video đơn B ngay
```

Không được bắt nhân viên bấm xác nhận chuyển đơn.

## 3. Workflow kết thúc ca

Chỉ dùng một QR lệnh:

```text
CMD:END_SHIFT
```

Khi camera thấy QR này:

```text
Nếu đang quay đơn hiện tại:
    dừng video hiện tại
    đưa video vào queue nén
    chuyển trạng thái SHIFT_ENDED

Nếu không quay đơn nào:
    chuyển trạng thái SHIFT_ENDED
```

Sau khi `SHIFT_ENDED`, hệ thống vẫn duy trì camera và QR scanner, nhưng không quay video cho đến khi thấy QR đơn mới.

## 4. Workflow bắt đầu chuỗi mới sau khi kết thúc ca

```text
Trạng thái SHIFT_ENDED
→ camera thấy QR đơn hàng mới
→ hệ thống tự tạo ca/chuỗi mới
→ bắt đầu quay video đơn mới ngay
```

Không yêu cầu bấm Start.

## 5. Quy tắc xử lý QR

### QR đơn hàng

- QR đơn hàng hợp lệ sẽ kích hoạt quay ngay.
- Nếu QR trùng với đơn đang quay: bỏ qua, tiếp tục quay.
- Nếu QR khác đơn đang quay: chuyển đơn ngay.

### QR kết thúc ca

- Nội dung chính xác: `CMD:END_SHIFT`
- Chỉ QR này có quyền kết thúc chuỗi quay.
- Để tránh quét nhầm, QR này nên được yêu cầu xuất hiện liên tục khoảng 1 giây trước khi thực thi.
- QR đơn hàng thì vẫn xử lý ngay, không cần chờ 1 giây.

## 6. Những điều cấm tự ý thay đổi

Codex/dev không được tự ý:

- Thêm nhiều QR lệnh điều khiển.
- Bắt nhân viên bấm nút mới quay.
- Bắt nhân viên bấm nút mới chuyển đơn.
- Bắt nhân viên bấm nút mới kết thúc ca.
- Đổi sang desktop app.
- Đổi sang cloud app.
- Giữ raw sau khi nén thành công.
- Tắt camera sau khi `CMD:END_SHIFT` nếu điều đó làm QR đơn mới không tự bắt đầu lại được.
- Dừng toàn bộ service sau `CMD:END_SHIFT`.

## 7. Trạng thái hệ thống

Các trạng thái chính:

```text
IDLE         : Camera chạy, chưa quay đơn nào.
RECORDING    : Đang quay một mã đơn.
SHIFT_ENDED  : Đã kết thúc ca, chờ QR đơn mới để bắt đầu lại.
ERROR        : Có lỗi camera/ghi file/nén nghiêm trọng.
```

Queue nén là tiến trình song song, không được làm thay đổi workflow quay chính.
