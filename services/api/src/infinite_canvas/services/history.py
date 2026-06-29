"""History list and delete — migrated from legacy main.py."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.paths import app_data_dir, coding_root

HISTORY_LOCK = Lock()


def _primary_history_file() -> Path:
    return app_data_dir() / "history.json"


def _legacy_history_file() -> Path:
    # Dev parity: upstream keeps history.json beside main.py under coding/Infinite-Canvas/.
    return coding_root() / "history.json"


def history_file_for_read() -> Path | None:
    """Prefer app data dir; fall back to legacy coding tree when present."""
    primary = _primary_history_file()
    if primary.is_file():
        return primary
    legacy = _legacy_history_file()
    if legacy.is_file():
        return legacy
    return None


def history_file_for_write() -> Path:
    """Write new history to app data; update legacy file if that is the active store."""
    primary = _primary_history_file()
    if primary.is_file():
        return primary
    legacy = _legacy_history_file()
    if legacy.is_file():
        return legacy
    return primary


def get_history(record_type: str | None = None) -> list[dict[str, Any]]:
    history_path = history_file_for_read()
    if history_path is None:
        return []
    try:
        with open(history_path, encoding="utf-8") as f:
            data: list[dict[str, Any]] = json.load(f)
    except Exception as exc:
        print(f"读取历史文件失败: {exc}")
        return []

    if record_type:
        data = [item for item in data if item.get("type", "zimage") == record_type]
    data = [item for item in data if item.get("images") and len(item["images"]) > 0]

    def sort_key(item: dict[str, Any]) -> float:
        ts = item.get("timestamp", 0)
        if isinstance(ts, (int, float)):
            return float(ts)
        return 0.0

    data.sort(key=sort_key, reverse=True)
    return data


def delete_history(timestamp: float) -> dict[str, Any]:
    history_path = history_file_for_read()
    if history_path is None:
        return {"success": False, "message": "History file not found"}

    try:
        with HISTORY_LOCK:
            with open(history_path, encoding="utf-8") as f:
                history: list[dict[str, Any]] = json.load(f)

            target_record: dict[str, Any] | None = None
            new_history: list[dict[str, Any]] = []
            for item in history:
                is_match = False
                item_ts = item.get("timestamp", 0)
                if isinstance(timestamp, (int, float)) and isinstance(item_ts, (int, float)):
                    if abs(float(item_ts) - float(timestamp)) < 0.001:
                        is_match = True
                elif str(item_ts) == str(timestamp):
                    is_match = True
                if is_match:
                    target_record = item
                else:
                    new_history.append(item)

            if target_record:
                write_path = history_file_for_write()
                write_path.parent.mkdir(parents=True, exist_ok=True)
                with open(write_path, "w", encoding="utf-8") as f:
                    json.dump(new_history, f, ensure_ascii=False, indent=4)

        if target_record:
            for img_url in target_record.get("images", []):
                file_path = output_file_from_url(img_url)
                if file_path and file_path.is_file():
                    try:
                        file_path.unlink()
                    except Exception as exc:
                        print(f"Failed to delete file {file_path}: {exc}")
            return {"success": True}
        return {"success": False, "message": "Record not found"}
    except Exception as exc:
        print(f"Delete history error: {exc}")
        return {"success": False, "message": str(exc)}
