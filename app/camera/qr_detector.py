from __future__ import annotations

from app.recording.order_parser import classify_qr


class QRDetector:
    def __init__(self, config: dict):
        self.config = config
        try:
            import cv2
        except Exception:
            self.cv2 = None
            self.detector = None
        else:
            self.cv2 = cv2
            self.detector = cv2.QRCodeDetector()

    def detect(self, frame) -> list[dict]:
        if self.detector is None:
            return []
        target = self._roi_frame(frame)
        values: list[str] = []
        try:
            ok, decoded_info, _points, _ = self.detector.detectAndDecodeMulti(target)
            if ok:
                values = [value for value in decoded_info if value]
        except Exception:
            value, _points, _ = self.detector.detectAndDecode(target)
            if value:
                values = [value]
        return [classify_qr(value) for value in values]

    def _roi_frame(self, frame):
        qr_config = self.config["qr"]
        if not qr_config.get("roi_enabled", False):
            return frame
        height, width = frame.shape[:2]
        roi = qr_config["roi"]
        x = int(width * roi["x"])
        y = int(height * roi["y"])
        w = int(width * roi["w"])
        h = int(height * roi["h"])
        return frame[max(0, y) : min(height, y + h), max(0, x) : min(width, x + w)]

