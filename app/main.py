from __future__ import annotations

from fastapi import FastAPI

from app.camera.capture import CameraService
from app.camera.frame_buffer import FrameBuffer
from app.camera.qr_detector import QRDetector
from app.compression.ffmpeg_worker import FFmpegWorker
from app.compression.queue import CompressionJob, CompressionQueue
from app.config import CONFIG
from app.db.database import connect, init_db
from app.db.repository import Repository
from app.recording.session_manager import SessionManager
from app.utils.logging import setup_logging
from app.utils.paths import ensure_dirs
from app.web.api import build_api_router
from app.web.routes import build_web_router, mount_static


ensure_dirs(CONFIG)
setup_logging(CONFIG["storage"]["logs_dir"])
init_db(CONFIG)
conn = connect(CONFIG)
repo = Repository(conn)
compression_queue = CompressionQueue()
session_manager = SessionManager(CONFIG, repo, compression_queue)
frame_buffer = FrameBuffer()
qr_detector = QRDetector(CONFIG)
camera_service = CameraService(CONFIG, frame_buffer, qr_detector, session_manager)
ffmpeg_worker = FFmpegWorker(CONFIG, repo, compression_queue)

app = FastAPI(title="Packing Video System")
mount_static(app)
app.include_router(build_web_router())
app.include_router(build_api_router(repo, session_manager, camera_service, compression_queue))


@app.on_event("startup")
def startup() -> None:
    for item in repo.unfinished_recordings():
        repo.mark_failed(item["id"], "App restarted while this video was still recording; raw file was kept for manual review")
        repo.log_event(
            "recording_recovered_failed",
            "Unfinished recording found during startup",
            {"video_id": item["id"], "raw_path": item.get("raw_path")},
        )
    for item in repo.pending_compression():
        raw_path = item.get("raw_path")
        if not raw_path:
            continue
        from pathlib import Path

        if Path(raw_path).exists():
            output_name = Path(raw_path).name.replace("_raw", "")
            output_path = Path(CONFIG["storage"]["videos_dir"]) / Path(raw_path).parent.name / output_name
            compression_queue.put(CompressionJob(item["id"], raw_path, str(output_path)))
        else:
            repo.mark_failed(item["id"], f"Raw file not found during startup recovery: {raw_path}")
    ffmpeg_worker.start()
    camera_service.start()


@app.on_event("shutdown")
def shutdown() -> None:
    camera_service.stop()
    ffmpeg_worker.stop()
    conn.close()
