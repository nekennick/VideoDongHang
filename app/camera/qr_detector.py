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
        target, transform = self._prepare_frame(frame)
        try:
            ok, decoded_info, points, _ = self.detector.detectAndDecodeMulti(target)
            if ok:
                detections: list[dict] = []
                for index, value in enumerate(decoded_info):
                    if not value:
                        continue
                    qr = classify_qr(value)
                    qr["qr_box"] = self._box_from_points(points[index], frame, transform)
                    detections.append(qr)
                if detections:
                    return detections
        except Exception:
            pass
        value, points, _ = self.detector.detectAndDecode(target)
        if value:
            qr = classify_qr(value)
            qr["qr_box"] = self._box_from_points(points, frame, transform)
            return [qr]
        return []

    def _prepare_frame(self, frame):
        height, width = frame.shape[:2]
        qr_config = self.config.get("qr", {})
        roi = qr_config.get("roi", {})
        offset_x = 0
        offset_y = 0
        target = frame

        if qr_config.get("roi_enabled"):
            x = self._to_pixels(roi.get("x", 0), width)
            y = self._to_pixels(roi.get("y", 0), height)
            w = self._to_pixels(roi.get("w", 1), width)
            h = self._to_pixels(roi.get("h", 1), height)
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            right = max(x + 1, min(width, x + w))
            bottom = max(y + 1, min(height, y + h))
            target = frame[y:bottom, x:right]
            offset_x = x
            offset_y = y

        scale = 1.0
        max_width = int(qr_config.get("detect_max_width", 960))
        if max_width > 0 and target.shape[1] > max_width:
            scale = max_width / target.shape[1]
            target = self.cv2.resize(target, None, fx=scale, fy=scale, interpolation=self.cv2.INTER_AREA)

        if len(target.shape) == 3:
            target = self.cv2.cvtColor(target, self.cv2.COLOR_BGR2GRAY)

        return target, {"offset_x": offset_x, "offset_y": offset_y, "scale": scale}

    def _to_pixels(self, value, size: int) -> int:
        number = float(value)
        if 0 <= number <= 1:
            return int(number * size)
        return int(number)

    def _box_from_points(self, points, frame, transform: dict) -> dict | None:
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
        scale = float(transform["scale"]) or 1.0
        offset_x = float(transform["offset_x"])
        offset_y = float(transform["offset_y"])
        xs = [(float(point[0]) / scale) + offset_x for point in point_list]
        ys = [(float(point[1]) / scale) + offset_y for point in point_list]
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
