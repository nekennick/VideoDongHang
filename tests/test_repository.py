from __future__ import annotations

import sqlite3
import unittest

from app.db.database import SCHEMA
from app.db.repository import Repository


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.repo = Repository(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_delete_video_removes_order_from_duplicate_check(self):
        video_id = self.repo.create_video(
            session_id="session",
            platform="unknown",
            order_code="ORDER_A",
            qr_content="ORDER_A",
            raw_path="data/raw/ORDER_A_raw.mp4",
        )

        self.assertTrue(self.repo.order_code_exists("ORDER_A"))
        self.repo.delete_video(video_id)

        self.assertIsNone(self.repo.get_video(video_id))
        self.assertFalse(self.repo.order_code_exists("ORDER_A"))


if __name__ == "__main__":
    unittest.main()
