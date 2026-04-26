from __future__ import annotations

import logging
import threading
import time

from app.camera.frame_buffer import FrameBuffer
from app.camera.qr_detector import QRDetector
from app.recording.session_manager import SessionManager

logger = logging.getLogger(__name__)


class CameraService:
    def __init__(self, config: dict, buffer: FrameBuffer, qr_detector: QRDetector, session_manager: SessionManager):
        self.config = config
        self.buffer = buffer
        self.qr_detector = qr_detector
        self.session_manager = session_manager
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="camera-capture", daemon=True)
        self._read_error_logged = False

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def _open_capture(self, cv2):
        camera = self.config["camera"]
        cap = cv2.VideoCapture(int(camera["index"]))
        if not cap.isOpened():
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(camera["width"]))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(camera["height"]))
        cap.set(cv2.CAP_PROP_FPS, int(camera["fps"]))
        return cap

    def _run(self) -> None:
        try:
            import cv2
        except Exception as exc:
            self.session_manager.camera_connected = False
            self.session_manager.camera_error = f"OpenCV not installed: {exc}"
            return

        camera = self.config["camera"]
        while not self._stop.is_set():
            cap = self._open_capture(cv2)
            if cap is None:
                self.session_manager.camera_connected = False
                self.session_manager.camera_error = "Cannot open camera"
                if not self._read_error_logged:
                    self.session_manager.repo.log_event("camera_error", "Cannot open camera", {"index": camera["index"]})
                    self._read_error_logged = True
                time.sleep(2)
                continue

            if self._read_error_logged:
                self._read_error_logged = False
            self.session_manager.camera_connected = True
            self.session_manager.camera_error = None
            self.session_manager.repo.log_event("camera_started", "Camera capture started", {"index": camera["index"]})

            failed_reads = 0
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    failed_reads += 1
                    self.session_manager.camera_connected = False
                    self.session_manager.camera_error = "Camera frame read failed"
                    if not self._read_error_logged:
                        self.session_manager.repo.log_event("camera_error", "Camera frame read failed", {"index": camera["index"]})
                        self._read_error_logged = True
                    if failed_reads >= 10:
                        break
                    time.sleep(0.5)
                    continue
                if self._read_error_logged:
                    self.session_manager.repo.log_event("camera_started", "Camera frame read recovered", {"index": camera["index"]})
                    self._read_error_logged = False
                failed_reads = 0
                self.session_manager.camera_connected = True
                self.session_manager.camera_error = None
                self.buffer.set(frame)
                self.session_manager.write_frame(frame)
                valid_qrs = [qr for qr in self.qr_detector.detect(frame) if qr.get("type") != "invalid"]
                self.session_manager.set_qr_detections([qr["qr_box"] for qr in valid_qrs if qr.get("qr_box")])
                has_end_shift = False
                for qr in valid_qrs:
                    if qr.get("type") == "end_shift":
                        has_end_shift = True
                    try:
                        self.session_manager.handle_qr(qr)
                    except Exception as exc:
                        logger.exception("Failed handling QR")
                        self.session_manager.set_error("Failed handling QR", exc)
                if not has_end_shift:
                    self.session_manager.reset_end_shift_debounce()
                time.sleep(0.001)
            cap.release()

    def mjpeg_frames(self):
        try:
            import cv2
        except Exception:
            return
        while True:
            frame = self.buffer.get()
            if frame is None:
                time.sleep(0.2)
                continue
            ok, jpg = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
