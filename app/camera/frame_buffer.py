from __future__ import annotations

import threading


class FrameBuffer:
    def __init__(self):
        self._lock = threading.Lock()
        self._frame = None

    def set(self, frame) -> None:
        with self._lock:
            self._frame = frame.copy()

    def get(self):
        with self._lock:
            return None if self._frame is None else self._frame.copy()

