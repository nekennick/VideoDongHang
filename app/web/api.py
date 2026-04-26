from __future__ import annotations

import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app.config import CONFIG, ConfigError, enforce_workflow_config, save_config
from app.db.repository import Repository
from app.recording.session_manager import SessionManager
from app.camera.capture import CameraService
from app.utils.paths import disk_free_gb


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except AttributeError as exc:
        raise HTTPException(status_code=501, detail="Open folder is only supported on Windows") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not open folder: {exc}") from exc


def _apply_config_update(current: dict, payload: dict[str, Any]) -> tuple[dict, bool]:
    allowed = {
        "camera": {"index", "width", "height", "fps", "backend"},
        "ffmpeg": {"path", "crf", "preset"},
        "storage": {"base_dir", "raw_dir", "videos_dir", "database_dir", "logs_dir", "min_free_disk_gb"},
        "qr": {"end_shift_debounce_seconds", "switch_order_cooldown_seconds", "roi_enabled", "roi"},
    }
    next_config = deepcopy(current)
    restart_required = False

    for section, values in payload.items():
        if section not in allowed or not isinstance(values, dict):
            raise HTTPException(status_code=400, detail=f"Unsupported config section: {section}")
        for key, value in values.items():
            if key not in allowed[section]:
                raise HTTPException(status_code=400, detail=f"Unsupported config key: {section}.{key}")
            if section == "qr" and key == "roi":
                if not isinstance(value, dict):
                    raise HTTPException(status_code=400, detail="qr.roi must be an object")
                roi = next_config["qr"].setdefault("roi", {})
                for roi_key, roi_value in value.items():
                    if roi_key not in {"x", "y", "w", "h"}:
                        raise HTTPException(status_code=400, detail=f"Unsupported config key: qr.roi.{roi_key}")
                    roi_float = float(roi_value)
                    if roi_float < 0 or roi_float > 1:
                        raise HTTPException(status_code=400, detail=f"qr.roi.{roi_key} must be between 0 and 1")
                    roi[roi_key] = roi_float
                continue
            if section == "camera" and key in {"index", "width", "height", "fps"}:
                value = int(value)
                minimum = 0 if key == "index" else 1
                if value < minimum:
                    raise HTTPException(status_code=400, detail=f"camera.{key} must be >= {minimum}")
            if section == "ffmpeg" and key == "crf":
                value = int(value)
                if value < 0 or value > 51:
                    raise HTTPException(status_code=400, detail="ffmpeg.crf must be between 0 and 51")
            if section == "storage" and key == "min_free_disk_gb":
                value = float(value)
                if value < 0:
                    raise HTTPException(status_code=400, detail="storage.min_free_disk_gb must be >= 0")
            if section == "qr" and key in {"end_shift_debounce_seconds", "switch_order_cooldown_seconds"}:
                value = float(value)
                if value < 0:
                    raise HTTPException(status_code=400, detail=f"qr.{key} must be >= 0")
            next_config[section][key] = value
            if section in {"camera", "storage"}:
                restart_required = True

    try:
        enforce_workflow_config(next_config)
    except ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    roi = next_config["qr"].get("roi", {})
    if roi.get("x", 0) + roi.get("w", 0) > 1 or roi.get("y", 0) + roi.get("h", 0) > 1:
        raise HTTPException(status_code=400, detail="qr.roi must fit inside the preview frame")
    return next_config, restart_required


def build_api_router(repo: Repository, session_manager: SessionManager, camera_service: CameraService, compression_queue) -> APIRouter:
    router = APIRouter()

    @router.get("/api/status")
    def status():
        free_gb = disk_free_gb(CONFIG["storage"]["base_dir"])
        min_free_gb = float(CONFIG["storage"].get("min_free_disk_gb", 20))
        session_manager.update_disk_status(free_gb, min_free_gb)
        snapshot = session_manager.status_snapshot(
            done_today=repo.count_done_today(),
            failed_today=repo.count_failed_today(),
            queue_size=compression_queue.size(),
            disk_free_gb=free_gb,
        )
        ffmpeg_path = str(CONFIG["ffmpeg"].get("path", "ffmpeg"))
        snapshot["ffmpeg_available"] = bool(shutil.which(ffmpeg_path) or Path(ffmpeg_path).exists())
        snapshot["ffmpeg_path"] = ffmpeg_path
        return snapshot

    @router.get("/api/videos")
    def videos(
        order_code: str | None = None,
        platform: str | None = None,
        status: str | None = None,
        date: str | None = None,
        limit: int = Query(default=50, ge=1, le=200),
    ):
        return {"items": repo.list_videos(order_code=order_code, platform=platform, status=status, date=date, limit=limit)}

    @router.get("/api/videos/{video_id}")
    def video(video_id: int):
        item = repo.get_video(video_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Video not found")
        return item

    @router.get("/video/{video_id}")
    def stream_video(video_id: int):
        item = repo.get_video(video_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Video not found")
        if item["status"] != "done" or not item["video_path"]:
            raise HTTPException(status_code=409, detail="Video is not ready")
        path = Path(item["video_path"])
        if not path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        return FileResponse(path, media_type="video/mp4")

    @router.get("/api/preview.mjpg")
    def preview():
        return StreamingResponse(camera_service.mjpeg_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

    @router.post("/api/admin/emergency-stop")
    def emergency_stop():
        session_manager.emergency_stop()
        return {"ok": True, "state": "SHIFT_ENDED"}

    @router.post("/api/admin/open-videos-folder")
    def open_videos_folder():
        path = Path(CONFIG["storage"]["videos_dir"])
        _open_folder(path)
        return {"ok": True, "path": str(path)}

    @router.post("/api/admin/open-video-folder/{video_id}")
    def open_video_folder(video_id: int):
        item = repo.get_video(video_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Video not found")
        path_value = item.get("video_path") or item.get("raw_path")
        if not path_value:
            raise HTTPException(status_code=409, detail="Video path is not available")
        folder = Path(path_value).parent
        _open_folder(folder)
        return {"ok": True, "path": str(folder)}

    @router.post("/api/admin/retry-compression/{video_id}")
    def retry_compression(video_id: int):
        item = repo.get_video(video_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Video not found")
        raw_path = item.get("raw_path")
        if not raw_path or not Path(raw_path).exists():
            raise HTTPException(status_code=409, detail="Raw file does not exist")
        output_name = Path(raw_path).name.replace("_raw", "")
        output_path = Path(CONFIG["storage"]["videos_dir"]) / Path(raw_path).parent.name / output_name
        from app.compression.queue import CompressionJob

        repo.mark_queued(video_id)
        compression_queue.put(CompressionJob(video_id, raw_path, str(output_path)))
        return {"ok": True}

    @router.get("/api/config")
    def get_config():
        public = {k: v for k, v in CONFIG.items() if k != "ffmpeg"}
        public["ffmpeg"] = {"crf": CONFIG["ffmpeg"]["crf"], "preset": CONFIG["ffmpeg"]["preset"]}
        return public

    @router.post("/api/config")
    def update_config(payload: dict[str, Any] = Body(...)):
        next_config, restart_required = _apply_config_update(CONFIG, payload)
        CONFIG.clear()
        CONFIG.update(next_config)
        save_config(CONFIG)
        from app.utils.paths import ensure_dirs

        ensure_dirs(CONFIG)
        return {"ok": True, "restart_required": restart_required, "config": get_config()}

    return router
