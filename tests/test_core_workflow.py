from __future__ import annotations

import unittest
from unittest.mock import patch

from app.compression.queue import CompressionQueue
from app.recording.order_parser import classify_qr, extract_order_code
from app.recording.session_manager import SessionManager


class FakeRepo:
    def __init__(self):
        self.next_id = 1
        self.videos = {}
        self.events = []
        self.states = {}

    def get_state(self, key):
        return self.states.get(key)

    def set_state(self, key, value):
        self.states[key] = value

    def create_video(self, **kwargs):
        video_id = self.next_id
        self.next_id += 1
        self.videos[video_id] = {"id": video_id, "status": "recording", **kwargs}
        return video_id

    def finish_recording(self, video_id, duration_seconds, raw_size_mb):
        self.videos[video_id]["status"] = "queued"
        self.videos[video_id]["duration_seconds"] = duration_seconds
        self.videos[video_id]["raw_size_mb"] = raw_size_mb

    def file_size_mb(self, path):
        return 1.0

    def log_event(self, event_type, message, metadata=None):
        self.events.append((event_type, message, metadata or {}))


class FakeWriter:
    def __init__(self, *args, **kwargs):
        self.closed = False
        self.frames = 0

    def write(self, frame):
        self.frames += 1

    def close(self):
        self.closed = True


def test_config():
    return {
        "camera": {"width": 1280, "height": 720, "fps": 20},
        "qr": {"end_shift_debounce_seconds": 1.0, "switch_order_cooldown_seconds": 0.0},
        "video": {"raw_codec": "mp4v", "raw_extension": ".mp4"},
        "storage": {"raw_dir": "data/raw", "videos_dir": "data/videos"},
    }


class CoreWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepo()
        self.queue = CompressionQueue()
        self.manager = SessionManager(test_config(), self.repo, self.queue)

    def test_order_parser_handles_supported_qr_shapes(self):
        self.assertEqual(extract_order_code("ORDER:250426ABC123"), "250426ABC123")
        self.assertEqual(extract_order_code("https://shop.local/?order_code=250426ABC123"), "250426ABC123")
        self.assertEqual(classify_qr("CMD:END_SHIFT")["type"], "end_shift")

    @patch("app.recording.session_manager.VideoWriter", FakeWriter)
    def test_first_order_starts_recording(self):
        self.manager.handle_order_qr("ORDER_A", "unknown", "ORDER_A")

        self.assertEqual(self.manager.state, "RECORDING")
        self.assertEqual(self.manager.current_order_code, "ORDER_A")
        self.assertEqual(len(self.repo.videos), 1)
        self.assertEqual(self.queue.size(), 0)

    @patch("app.recording.session_manager.VideoWriter", FakeWriter)
    def test_duplicate_order_is_ignored(self):
        self.manager.handle_order_qr("ORDER_A", "unknown", "ORDER_A")
        self.manager.handle_order_qr("ORDER_A", "unknown", "ORDER_A")

        self.assertEqual(len(self.repo.videos), 1)
        self.assertEqual(self.queue.size(), 0)

    @patch("app.recording.session_manager.VideoWriter", FakeWriter)
    def test_new_order_queues_previous_video(self):
        self.manager.handle_order_qr("ORDER_A", "unknown", "ORDER_A")
        self.manager.handle_order_qr("ORDER_B", "unknown", "ORDER_B")

        self.assertEqual(self.manager.state, "RECORDING")
        self.assertEqual(self.manager.current_order_code, "ORDER_B")
        self.assertEqual(len(self.repo.videos), 2)
        self.assertEqual(self.queue.size(), 1)
        self.assertEqual(self.repo.videos[1]["status"], "queued")

    @patch("app.recording.session_manager.VideoWriter", FakeWriter)
    @patch("app.recording.session_manager.time.monotonic")
    def test_end_shift_requires_debounce(self, monotonic):
        monotonic.side_effect = [10.0, 10.0, 10.0, 10.0, 10.5, 11.1, 11.2]
        self.manager.handle_order_qr("ORDER_A", "unknown", "ORDER_A")

        self.manager.handle_end_shift_qr()
        self.assertEqual(self.manager.state, "RECORDING")

        self.manager.handle_end_shift_qr()
        self.assertEqual(self.manager.state, "RECORDING")

        self.manager.handle_end_shift_qr()
        self.assertEqual(self.manager.state, "SHIFT_ENDED")
        self.assertIsNone(self.manager.current_order_code)
        self.assertEqual(self.queue.size(), 1)

    @patch("app.recording.session_manager.VideoWriter", FakeWriter)
    def test_order_after_shift_ended_restarts_recording(self):
        self.manager.state = "SHIFT_ENDED"
        self.manager.handle_order_qr("ORDER_C", "unknown", "ORDER_C")

        self.assertEqual(self.manager.state, "RECORDING")
        self.assertEqual(self.manager.current_order_code, "ORDER_C")


if __name__ == "__main__":
    unittest.main()
