# TEST PLAN

## 1. Test QR đơn đầu tiên

Input:

```text
QR: ORDER_A
State: IDLE
```

Expected:

```text
State = RECORDING
current_order_code = ORDER_A
Có file raw ORDER_A
Database có record ORDER_A status recording
```

## 2. Test QR trùng đơn hiện tại

Input:

```text
Đang quay ORDER_A
Camera thấy ORDER_A lại
```

Expected:

```text
Không tạo video mới
Không cắt video hiện tại
Tiếp tục quay ORDER_A
```

## 3. Test chuyển đơn

Input:

```text
Đang quay ORDER_A
Camera thấy ORDER_B
```

Expected:

```text
Dừng ORDER_A
ORDER_A vào queue nén
Bắt đầu ORDER_B ngay
State vẫn RECORDING
```

## 4. Test kết thúc ca bằng QR duy nhất

Input:

```text
Đang quay ORDER_B
Camera thấy CMD:END_SHIFT liên tục 1 giây
```

Expected:

```text
Dừng ORDER_B
ORDER_B vào queue nén
State = SHIFT_ENDED
current_order_code = null
Camera vẫn hoạt động
QR scanner vẫn hoạt động
```

## 5. Test bắt đầu lại sau kết thúc ca

Input:

```text
State = SHIFT_ENDED
Camera thấy ORDER_C
```

Expected:

```text
Tạo chuỗi/session mới nếu cần
Bắt đầu quay ORDER_C ngay
State = RECORDING
```

## 6. Test nén thành công

Input:

```text
Raw file ORDER_A tồn tại
Compression worker chạy
```

Expected:

```text
Tạo file nén trong videos/YYYY-MM-DD
Database status = done
compression_status = done
deleted_raw = 1
Raw file bị xóa
```

## 7. Test nén lỗi

Input:

```text
FFmpeg lỗi
```

Expected:

```text
Database status = failed hoặc compression_status = failed
Raw file vẫn còn
error_message có nội dung lỗi
Không crash app
```

## 8. Test mất camera

Input:

```text
Rút/mất iVCAM
```

Expected:

```text
Web báo camera disconnected
App không crash
Nếu đang quay, dừng an toàn hoặc chuyển ERROR tùy implementation
Ghi log camera_error
```

## 9. Test 200 đơn/ngày mô phỏng

Input:

```text
Quét 200 QR khác nhau, mỗi đơn 10-30 giây hoặc mô phỏng nhanh
```

Expected:

```text
Không treo app
Không mất record database
Queue nén xử lý lần lượt
Video sau nén tìm được theo mã đơn
Raw đã nén thành công đều bị xóa
```
