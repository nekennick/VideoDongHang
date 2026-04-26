from __future__ import annotations

from dataclasses import dataclass
from queue import Queue


@dataclass(frozen=True)
class CompressionJob:
    video_id: int
    raw_path: str
    output_path: str


class CompressionQueue:
    def __init__(self):
        self._queue: Queue[CompressionJob] = Queue()

    def put(self, job: CompressionJob) -> None:
        self._queue.put(job)

    def get(self, timeout: float = 1.0) -> CompressionJob:
        return self._queue.get(timeout=timeout)

    def task_done(self) -> None:
        self._queue.task_done()

    def size(self) -> int:
        return self._queue.qsize()

