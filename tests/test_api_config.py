from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.web.api import _apply_config_update


def base_config():
    return {
        "camera": {"index": 0, "width": 1280, "height": 720, "fps": 20, "backend": "auto"},
        "qr": {
            "end_shift_command": "CMD:END_SHIFT",
            "end_shift_debounce_seconds": 1.0,
            "order_qr_process_immediately": True,
            "switch_order_cooldown_seconds": 0.3,
            "roi_enabled": True,
            "roi": {"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35},
        },
        "video": {"raw_codec": "mp4v", "raw_extension": ".mp4", "compressed_extension": ".mp4", "include_audio": False},
        "ffmpeg": {"path": "ffmpeg", "crf": 28, "preset": "veryfast"},
        "storage": {
            "base_dir": "data",
            "raw_dir": "data/raw",
            "videos_dir": "data/videos",
            "database_dir": "data/database",
            "logs_dir": "data/logs",
            "delete_raw_after_success": True,
            "min_free_disk_gb": 20,
        },
        "web": {"host": "127.0.0.1", "port": 8000},
    }


class ConfigUpdateTest(unittest.TestCase):
    def test_allows_safe_ffmpeg_update(self):
        config, restart_required = _apply_config_update(base_config(), {"ffmpeg": {"crf": 30}})

        self.assertFalse(restart_required)
        self.assertEqual(config["ffmpeg"]["crf"], 30)

    def test_allows_safe_roi_update(self):
        config, restart_required = _apply_config_update(base_config(), {"qr": {"roi": {"x": 0.1, "w": 0.2}}})

        self.assertFalse(restart_required)
        self.assertEqual(config["qr"]["roi"]["x"], 0.1)
        self.assertEqual(config["qr"]["roi"]["w"], 0.2)

    def test_rejects_workflow_command_change(self):
        with self.assertRaises(HTTPException) as raised:
            _apply_config_update(base_config(), {"qr": {"end_shift_command": "CMD:STOP"}})

        self.assertEqual(raised.exception.status_code, 400)

    def test_rejects_roi_outside_frame(self):
        with self.assertRaises(HTTPException) as raised:
            _apply_config_update(base_config(), {"qr": {"roi": {"x": 0.9, "w": 0.2}}})

        self.assertEqual(raised.exception.status_code, 400)

    def test_rejects_invalid_camera_fps(self):
        with self.assertRaises(HTTPException) as raised:
            _apply_config_update(base_config(), {"camera": {"fps": 0}})

        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
