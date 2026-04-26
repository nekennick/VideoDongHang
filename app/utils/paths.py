from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.utils.time import today_text


SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def ensure_dirs(config: dict) -> None:
    storage = config["storage"]
    for key in ["base_dir", "raw_dir", "videos_dir", "database_dir", "logs_dir"]:
        Path(storage[key]).mkdir(parents=True, exist_ok=True)


def sanitize_part(value: str) -> str:
    cleaned = SAFE_NAME_RE.sub("_", value.strip())
    cleaned = cleaned.strip("._")
    return cleaned[:120] or "UNKNOWN"


def dated_dir(base_dir: str) -> Path:
    path = Path(base_dir) / today_text()
    path.mkdir(parents=True, exist_ok=True)
    return path


def disk_free_gb(path: str) -> float:
    usage = shutil.disk_usage(Path(path).resolve())
    return round(usage.free / (1024**3), 2)

