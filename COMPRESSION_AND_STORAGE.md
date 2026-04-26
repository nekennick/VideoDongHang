# COMPRESSION AND STORAGE

## 1. Nguyên tắc

- Quay video raw trước để giảm rủi ro lỗi khi đang ghi.
- Sau khi kết thúc mỗi đơn, đưa raw vào compression queue.
- Compression worker chạy nền.
- Không được chặn luồng quay chính.
- Nén xong thành công thì xóa raw.
- Nén lỗi thì giữ raw.

## 2. FFmpeg command đề xuất

```bash
ffmpeg -y -i input_raw.mp4 -an -vcodec libx264 -preset veryfast -crf 28 -movflags +faststart output.mp4
```

Giải thích:

- `-y`: ghi đè output nếu cần.
- `-an`: bỏ âm thanh.
- `libx264`: chuẩn H.264 dễ xem.
- `preset veryfast`: nén nhanh, phù hợp vừa quay vừa xử lý.
- `crf 28`: cân bằng dung lượng và chất lượng.
- `+faststart`: xem trên web nhanh hơn.

## 3. Queue nén

Job gồm:

```json
{
  "video_id": 123,
  "raw_path": "data/raw/2026-04-26/file_raw.mp4",
  "output_path": "data/videos/2026-04-26/file.mp4"
}
```

## 4. Quy trình nén

```text
Nhận job
→ cập nhật status = compressing
→ chạy FFmpeg
→ kiểm tra output tồn tại và size > 0
→ cập nhật status = done
→ ghi compressed_size_mb
→ xóa raw
→ cập nhật deleted_raw = 1
```

Nếu lỗi:

```text
FFmpeg lỗi hoặc output không hợp lệ
→ cập nhật status = failed
→ compression_status = failed
→ giữ raw
→ ghi error_message
```

## 5. Dọn dẹp raw khi app khởi động

Khi app startup:

- Kiểm tra database xem có video nào status `queued` hoặc `compressing` dang dở.
- Nếu raw còn tồn tại, đưa lại vào queue nén.
- Nếu raw mất, đánh dấu failed và ghi lỗi.

## 6. Cảnh báo dung lượng ổ cứng

Config:

```json
{
  "min_free_disk_gb": 20
}
```

Nếu thấp hơn ngưỡng:

- Hiển thị cảnh báo đỏ trên web.
- Ghi system event.
- Không tự ý xóa video nén nếu chưa có chức năng retention được duyệt.

## 7. Retention

Không tự ý xóa video nén cũ.

Nếu muốn thêm retention 30/60/90 ngày, phải hỏi chủ dự án trước.
