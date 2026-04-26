from __future__ import annotations

import logging
import threading
import time
import uuid
from pathlib import Path

from app.compression.queue import CompressionJob, CompressionQueue
from app.db.repository import Repository
from app.recording.video_writer import VideoWriter
from app.utils.paths import dated_dir, sanitize_part
from app.utils.time import now_local

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, config: dict, repo: Repository, compression_queue: CompressionQueue):
        self.config = config
        self.repo = repo
        self.compression_queue = compression_queue
        self.lock = threading.RLock()
        saved_state = repo.get_state("current_state")
        self.state = saved_state if saved_state in {"SHIFT_ENDED"} else "IDLE"
        self.session_id: str | None = repo.get_state("current_session_id")
        self.current_video_id: int | None = None
        self.current_order_code: str | None = None
        self.current_platform = "unknown"
        self.current_raw_path: str | None = None
        self.current_start_monotonic: float | None = None
        self.writer: VideoWriter | None = None
        self.last_qr_content: str | None = None
        self.last_qr_at: float | None = None
        self._end_shift_seen_since: float | None = None
        self._last_switch_at = 0.0
        self.camera_connected = False
        self.camera_error: str | None = None
        self.disk_warning_active = False
        self.qr_detections: list[dict] = []
        self.last_ignored_order_code: str | None = None
        self.last_ignored_reason: str | None = None
        self._last_duplicate_log_at: dict[str, float] = {}
        self._finalizer_threads: list[threading.Thread] = []

    def write_frame(self, frame) -> None:
        with self.lock:
            if self.state == "RECORDING" and self.writer is not None:
                try:
                    self.writer.write(frame)
                except Exception as exc:
                    self.state = "ERROR"
                    self.camera_error = str(exc)
                    self.repo.log_event("camera_error", "Failed writing video frame", {"error": str(exc)})

    def handle_qr(self, qr: dict) -> None:
        qr_type = qr.get("type")
        self.last_qr_content = qr.get("raw_content")
        self.last_qr_at = time.monotonic()
        if qr_type == "order":
            self._end_shift_seen_since = None
            self.handle_order_qr(qr["order_code"], qr.get("platform", "unknown"), qr.get("raw_content", ""))
        elif qr_type == "end_shift":
            self.handle_end_shift_qr()

    def reset_end_shift_debounce(self) -> None:
        with self.lock:
            self._end_shift_seen_since = None

    def set_qr_detections(self, detections: list[dict]) -> None:
        with self.lock:
            self.qr_detections = detections

    def set_error(self, message: str, exc: Exception | None = None) -> None:
        with self.lock:
            detail = str(exc) if exc else message
            self.state = "ERROR"
            self.camera_error = detail
            self.repo.set_state("current_state", self.state)
            self.repo.log_event("camera_error", message, {"error": detail})

    def clear_ignored_order(self, order_code: str) -> None:
        with self.lock:
            if self.last_ignored_order_code == order_code:
                self.last_ignored_order_code = None
                self.last_ignored_reason = None
            self._last_duplicate_log_at.pop(order_code, None)

    def handle_order_qr(self, order_code: str, platform: str, raw_content: str) -> None:
        with self.lock:
            if self.state == "RECORDING" and order_code == self.current_order_code:
                return
            if self.repo.order_code_exists(order_code):
                self.last_ignored_order_code = order_code
                self.last_ignored_reason = "duplicate_order"
                now = time.monotonic()
                last_log_at = self._last_duplicate_log_at.get(order_code, 0.0)
                if now - last_log_at >= 2.0:
                    self._last_duplicate_log_at[order_code] = now
                    self.repo.log_event(
                        "duplicate_order_ignored",
                        "Duplicate order QR ignored",
                        {"order_code": order_code, "current_order_code": self.current_order_code},
                    )
                return
            now = time.monotonic()
            cooldown = float(self.config["qr"].get("switch_order_cooldown_seconds", 0.3))
            if self.state == "RECORDING" and now - self._last_switch_at < cooldown:
                return
            if self.state in {"IDLE", "SHIFT_ENDED"}:
                self._start_new_session()
                self._start_recording(order_code, platform, raw_content)
                return
            if self.state == "RECORDING":
                self._stop_current_recording()
                self._start_recording(order_code, platform, raw_content)

    def handle_end_shift_qr(self) -> None:
        with self.lock:
            now = time.monotonic()
            if self._end_shift_seen_since is None:
                self._end_shift_seen_since = now
                return
            debounce = float(self.config["qr"]["end_shift_debounce_seconds"])
            if now - self._end_shift_seen_since < debounce:
                return
            if self.state == "SHIFT_ENDED":
                self._end_shift_seen_since = now
                return
            if self.state == "RECORDING":
                self._stop_current_recording()
            self.state = "SHIFT_ENDED"
            self.current_order_code = None
            self.current_platform = "unknown"
            self._end_shift_seen_since = now
            self.repo.set_state("current_state", self.state)
            self.repo.log_event("end_shift_detected", "Shift ended by CMD:END_SHIFT", {})

    def emergency_stop(self) -> None:
        with self.lock:
            if self.state == "RECORDING":
                self._stop_current_recording()
            self.state = "SHIFT_ENDED"
            self.current_order_code = None
            self.current_platform = "unknown"
            self.repo.set_state("current_state", self.state)
            self.repo.log_event("end_shift_detected", "Emergency stop from admin API", {})

    def wait_for_finalizers(self, timeout: float | None = None) -> None:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self.lock:
                threads = list(self._finalizer_threads)
            if not threads:
                return
            for thread in threads:
                remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
                thread.join(timeout=remaining)
            with self.lock:
                self._finalizer_threads = [thread for thread in self._finalizer_threads if thread.is_alive()]
            if deadline is not None and time.monotonic() >= deadline:
                return

    def _start_new_session(self) -> None:
        if self.state == "SHIFT_ENDED" or not self.session_id:
            self.session_id = uuid.uuid4().hex
            self.repo.set_state("current_session_id", self.session_id)

    def _start_recording(self, order_code: str, platform: str, raw_content: str) -> None:
        assert self.session_id is not None
        camera = self.config["camera"]
        video = self.config["video"]
        stamp = now_local().strftime("%Y-%m-%d_%H-%M-%S")
        safe_order = sanitize_part(order_code)
        safe_platform = sanitize_part(platform.upper())
        raw_name = f"{stamp}_{safe_platform}_{safe_order}_raw{video['raw_extension']}"
        raw_path = dated_dir(self.config["storage"]["raw_dir"]) / raw_name
        try:
            self.writer = VideoWriter(str(raw_path), int(camera["width"]), int(camera["height"]), int(camera["fps"]), video["raw_codec"])
        except Exception as exc:
            self.set_error("Failed starting video writer", exc)
            return
        video_id = self.repo.create_video(
            session_id=self.session_id,
            platform=platform,
            order_code=order_code,
            qr_content=raw_content,
            raw_path=str(raw_path),
        )
        self.current_video_id = video_id
        self.current_order_code = order_code
        self.current_platform = platform
        self.current_raw_path = str(raw_path)
        self.current_start_monotonic = time.monotonic()
        self.last_ignored_order_code = None
        self.last_ignored_reason = None
        self.state = "RECORDING"
        self._last_switch_at = time.monotonic()
        self.repo.set_state("current_state", self.state)
        self.repo.set_state("last_order_code", order_code)
        self.repo.log_event("order_started", "Order recording started", {"video_id": video_id, "order_code": order_code})

    def _stop_current_recording(self) -> None:
        if not self.writer or self.current_video_id is None or self.current_raw_path is None:
            return
        writer = self.writer
        video_id = self.current_video_id
        raw_path = self.current_raw_path
        start_monotonic = self.current_start_monotonic
        duration = 0.0
        if start_monotonic is not None:
            duration = max(0.0, time.monotonic() - start_monotonic)

        self.writer = None
        self.current_video_id = None
        self.current_order_code = None
        self.current_raw_path = None
        self.current_start_monotonic = None

        thread = threading.Thread(
            target=self._finalize_recording,
            args=(writer, video_id, raw_path, duration),
            name=f"recording-finalizer-{video_id}",
            daemon=True,
        )
        self._finalizer_threads.append(thread)
        thread.start()

    def _finalize_recording(self, writer: VideoWriter, video_id: int, raw_path: str, duration: float) -> None:
        try:
            writer.close()
            raw_size_mb = self.repo.file_size_mb(raw_path)
            self.repo.finish_recording(video_id, duration, raw_size_mb)
            output_name = Path(raw_path).name.replace("_raw", "")
            output_path = dated_dir(self.config["storage"]["videos_dir"]) / output_name
            self.compression_queue.put(CompressionJob(video_id, raw_path, str(output_path)))
            self.repo.log_event("order_stopped", "Order recording stopped and queued", {"video_id": video_id})
        except Exception as exc:
            logger.exception("Failed finalizing recording")
            self.repo.mark_failed(video_id, f"Failed finalizing recording: {exc}")
            self.repo.log_event("recording_finalize_failed", "Failed finalizing recording", {"video_id": video_id, "error": str(exc)})
        finally:
            with self.lock:
                current = threading.current_thread()
                self._finalizer_threads = [thread for thread in self._finalizer_threads if thread is not current and thread.is_alive()]

    def update_disk_status(self, disk_free_gb: float, min_free_disk_gb: float) -> None:
        with self.lock:
            is_low = disk_free_gb < min_free_disk_gb
            if is_low and not self.disk_warning_active:
                self.repo.log_event(
                    "disk_space_low",
                    "Free disk space is below configured threshold",
                    {"disk_free_gb": disk_free_gb, "min_free_disk_gb": min_free_disk_gb},
                )
            self.disk_warning_active = is_low

    def status_snapshot(self, done_today: int, failed_today: int, queue_size: int, disk_free_gb: float) -> dict:
        with self.lock:
            duration = 0.0
            if self.state == "RECORDING" and self.current_start_monotonic is not None:
                duration = time.monotonic() - self.current_start_monotonic
            min_free_disk_gb = float(self.config["storage"].get("min_free_disk_gb", 20))
            return {
                "state": self.state,
                "current_order_code": self.current_order_code,
                "current_platform": self.current_platform,
                "current_duration_seconds": round(duration, 1),
                "compression_queue_size": queue_size,
                "done_today": done_today,
                "failed_today": failed_today,
                "disk_free_gb": disk_free_gb,
                "min_free_disk_gb": min_free_disk_gb,
                "disk_space_low": self.disk_warning_active,
                "camera_connected": self.camera_connected,
                "camera_error": self.camera_error,
                "last_qr_content": self.last_qr_content,
                "last_ignored_order_code": self.last_ignored_order_code,
                "last_ignored_reason": self.last_ignored_reason,
                "qr_detections": list(self.qr_detections),
            }
