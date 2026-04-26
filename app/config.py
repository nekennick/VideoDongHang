from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
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


class ConfigError(RuntimeError):
    pass


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def enforce_workflow_config(config: dict[str, Any]) -> None:
    qr = config.setdefault("qr", {})
    storage = config.setdefault("storage", {})
    if qr.get("end_shift_command") != "CMD:END_SHIFT":
        raise ConfigError("qr.end_shift_command must remain CMD:END_SHIFT")
    if qr.get("order_qr_process_immediately") is not True:
        raise ConfigError("qr.order_qr_process_immediately must remain true")
    if storage.get("delete_raw_after_success") is not True:
        raise ConfigError("storage.delete_raw_after_success must remain true")


def load_config(path: str | Path = "config.json") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
    user_config = json.loads(config_path.read_text(encoding="utf-8"))
    config = _deep_merge(DEFAULT_CONFIG, user_config)
    enforce_workflow_config(config)
    return config


def save_config(config: dict[str, Any], path: str | Path = "config.json") -> None:
    enforce_workflow_config(config)
    Path(path).write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


CONFIG = load_config()
