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
        target = frame
        try:
            ok, decoded_info, points, _ = self.detector.detectAndDecodeMulti(target)
            if ok:
                detections: list[dict] = []
                for index, value in enumerate(decoded_info):
                    if not value:
                        continue
                    qr = classify_qr(value)
                    qr["qr_box"] = self._box_from_points(points[index], frame)
                    detections.append(qr)
                return detections
        except Exception:
            value, points, _ = self.detector.detectAndDecode(target)
            if value:
                qr = classify_qr(value)
                qr["qr_box"] = self._box_from_points(points, frame)
                return [qr]
        return []

    def _box_from_points(self, points, frame) -> dict | None:
        if points is None:
            return None
        height, width = frame.shape[:2]
        point_list = points.tolist() if hasattr(points, "tolist") else points
        if not point_list:
            return None
        if point_list and isinstance(point_list[0][0], list):
            point_list = point_list[0]
        if not point_list:
            return None
        xs = [float(point[0]) for point in point_list]
        ys = [float(point[1]) for point in point_list]
        left = max(0.0, min(xs) / width)
        top = max(0.0, min(ys) / height)
        right = min(1.0, max(xs) / width)
        bottom = min(1.0, max(ys) / height)
        return {
            "x": round(left, 4),
            "y": round(top, 4),
            "w": round(max(0.0, right - left), 4),
            "h": round(max(0.0, bottom - top), 4),
        }
