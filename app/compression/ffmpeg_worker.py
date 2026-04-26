from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path
from queue import Empty

from app.compression.queue import CompressionJob, CompressionQueue
from app.db.repository import Repository

logger = logging.getLogger(__name__)


class FFmpegWorker:
    def __init__(self, config: dict, repo: Repository, queue: CompressionQueue):
        self.config = config
        self.repo = repo
        self.queue = queue
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ffmpeg-worker", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                job = self.queue.get(timeout=1)
            except Empty:
                continue
            try:
                self.compress(job)
            finally:
                self.queue.task_done()

    def compress(self, job: CompressionJob) -> None:
        raw = Path(job.raw_path)
        output = Path(job.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not raw.exists():
            self.repo.mark_failed(job.video_id, f"Raw file not found: {raw}")
            self.repo.log_event("compression_failed", "Raw file missing", {"video_id": job.video_id, "raw_path": str(raw)})
            return

        self.repo.mark_compressing(job.video_id)
        self.repo.log_event("compression_started", "Compression started", {"video_id": job.video_id})
        ffmpeg = self.config["ffmpeg"]
        video = self.config["video"]
        cmd = [
            ffmpeg["path"],
            "-y",
            "-i",
            str(raw),
        ]
        if not video.get("include_audio", False):
            cmd.append("-an")
        cmd.extend(["-vcodec", "libx264", "-preset", str(ffmpeg["preset"]), "-crf", str(ffmpeg["crf"]), "-movflags", "+faststart", str(output)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=None)
        except Exception as exc:
            self.repo.mark_failed(job.video_id, str(exc))
            self.repo.log_event("compression_failed", "FFmpeg could not run", {"video_id": job.video_id, "error": str(exc)})
            return

        if result.returncode != 0 or not output.exists() or output.stat().st_size <= 0:
            message = result.stderr[-1000:] or "FFmpeg failed or output is empty"
            self.repo.mark_failed(job.video_id, message)
            self.repo.log_event("compression_failed", "FFmpeg failed", {"video_id": job.video_id, "error": message})
            return

        deleted_raw = False
        if self.config["storage"]["delete_raw_after_success"]:
            try:
                raw.unlink()
                deleted_raw = True
                self.repo.log_event("raw_deleted", "Raw file deleted after successful compression", {"raw_path": str(raw)})
            except OSError as exc:
                self.repo.log_event("raw_delete_failed", "Could not delete raw file", {"raw_path": str(raw), "error": str(exc)})

        compressed_size_mb = round(output.stat().st_size / (1024 * 1024), 2)
        self.repo.mark_done(job.video_id, str(output), compressed_size_mb, deleted_raw)
        self.repo.log_event("compression_done", "Compression completed", {"video_id": job.video_id, "output_path": str(output)})

