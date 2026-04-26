# Packing Video System

Web local tren Windows de quay video dong hang bang camera iVCAM, tu dong cat video theo QR don hang va nen video bang FFmpeg.

## Workflow bat buoc

```text
QR don dau tien -> bat dau quay ngay
QR don moi -> dung video hien tai, dua vao queue nen, quay don moi ngay
CMD:END_SHIFT -> ket thuc ca, dung video hien tai neu dang quay
Sau SHIFT_ENDED, QR don moi -> tu bat dau chuoi quay moi
```

Chi co mot QR lenh trong workflow chinh:

```text
CMD:END_SHIFT
```

Khong them STOP/PAUSE/RESUME/LOCK/UNLOCK neu chua duoc chu du an duyet.

## Yeu cau

- Windows 11.
- Python 3.11+.
- iVCAM da ket noi va xuat hien nhu webcam.
- FFmpeg co trong `PATH`, hoac sua `ffmpeg.path` trong `config.json`.

Kiem tra FFmpeg:

```bat
ffmpeg -version
```

## Chay app

Chay file:

```bat
run.bat
```

Sau do mo:

```text
http://127.0.0.1:8000
```

`run.bat` se tao `.venv`, cai `requirements.txt`, roi chay FastAPI.

## Cau hinh

File cau hinh chinh:

```text
config.json
```

Co the sua nhanh tren web o muc "Cau hinh nhanh" cho cac gia tri an toan:

- Camera index, width, height, FPS.
- FFmpeg CRF, preset.
- Nguong canh bao o dia trong.
- Vung ROI doc QR.

Mot so thay doi camera/storage can khoi dong lai app de ap dung. API va UI khong cho sua cac quy tac workflow bat buoc nhu `CMD:END_SHIFT`, xu ly QR don ngay, va xoa raw sau khi nen thanh cong.

## Luu tru

- Raw tam: `data/raw/YYYY-MM-DD/`
- Video da nen: `data/videos/YYYY-MM-DD/`
- SQLite: `data/database/packing_video.db`
- Log: `data/logs/app.log`

Raw se bi xoa sau khi nen thanh cong. Neu nen loi, raw duoc giu lai va record duoc danh dau `failed`.

## API chinh

- `GET /api/status`
- `GET /api/videos`
- `GET /api/videos/{id}`
- `GET /video/{id}`
- `GET /api/preview.mjpg`
- `POST /api/admin/emergency-stop`
- `POST /api/admin/retry-compression/{id}`
- `POST /api/admin/open-videos-folder`
- `POST /api/admin/open-video-folder/{id}`
- `GET /api/config`
- `POST /api/config`

## Test

Chay test tu dong:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests
```

Test hien co kiem tra workflow QR cot loi va validation config an toan.

## Tai lieu du an

- `PROJECT_REQUIREMENTS.md`
- `MANDATORY_WORKFLOW.md`
- `ROADMAP_TASKS.md`
- `TEST_PLAN.md`
- `API_SPEC.md`
- `DATABASE_SCHEMA.md`
- `VIDEO_QR_LOGIC.md`
- `COMPRESSION_AND_STORAGE.md`
- `FRONTEND_SPEC.md`
- `CONFIG_SPEC.md`
- `CODEX_INSTRUCTIONS.md`
