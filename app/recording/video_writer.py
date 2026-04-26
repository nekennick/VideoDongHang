from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoWriter:
    def __init__(self, path: str, width: int, height: int, fps: int, codec: str):
        self.path = path
        self.width = width
        self.height = height
        self.frame_count = 0
        try:
            import cv2
        except Exception as exc:  # pragma: no cover - depends on local install
            raise RuntimeError(f"OpenCV is required for recording: {exc}") from exc
        self.cv2 = cv2
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        self._writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
        if not self._writer.isOpened():
            raise RuntimeError(f"Cannot open video writer: {path}")

    def write(self, frame) -> None:
        height, width = frame.shape[:2]
        if width != self.width or height != self.height:
            frame = self.cv2.resize(frame, (self.width, self.height))
        self._writer.write(frame)
        self.frame_count += 1

    def close(self) -> None:
        self._writer.release()
