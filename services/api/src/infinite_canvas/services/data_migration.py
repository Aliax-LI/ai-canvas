"""One-time import of legacy JSON files into SQLite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infinite_canvas.core.database import (
    is_migration_done,
    mark_migration_done,
    set_setting,
    upsert_canvas,
    upsert_conversation,
    upsert_project,
)
from infinite_canvas.core.paths import (
    api_providers_file,
    canvases_dir,
    conversations_dir,
    legacy_canvases_dir,
    legacy_projects_file,
    projects_file,
)
from infinite_canvas.core.websocket import now_ms


def _load_json_file(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _canvas_dirs_to_scan() -> list[Path]:
    dirs: list[Path] = []
    for directory in (canvases_dir(), legacy_canvases_dir()):
        if directory.is_dir() and any(directory.glob("*.json")):
            if directory not in dirs:
                dirs.append(directory)
    return dirs


def _projects_file_candidates() -> list[Path]:
    paths: list[Path] = []
    for path in (projects_file(), legacy_projects_file()):
        if path.is_file() and path not in paths:
            paths.append(path)
    return paths


def import_projects_from_files() -> int:
    count = 0
    for path in _projects_file_candidates():
        raw = _load_json_file(path)
        if raw is None:
            continue
        projects = raw.get("projects") if isinstance(raw, dict) else raw
        if not isinstance(projects, list):
            continue
        for item in projects:
            if isinstance(item, dict) and item.get("id"):
                upsert_project(item)
                count += 1
    return count


def import_canvases_from_files() -> int:
    count = 0
    seen: set[str] = set()
    for directory in _canvas_dirs_to_scan():
        for file_path in directory.glob("*.json"):
            raw = _load_json_file(file_path)
            if not isinstance(raw, dict) or not raw.get("id"):
                continue
            canvas_id = str(raw["id"])
            if canvas_id in seen:
                continue
            seen.add(canvas_id)
            upsert_canvas(raw)
            count += 1
    return count


def import_conversations_from_files() -> int:
    count = 0
    root = conversations_dir()
    if not root.is_dir():
        return 0
    for user_dir in root.iterdir():
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name
        for file_path in user_dir.glob("*.json"):
            raw = _load_json_file(file_path)
            if not isinstance(raw, dict) or not raw.get("id"):
                continue
            upsert_conversation(user_id, raw)
            count += 1
    return count


def import_providers_from_files() -> int:
    path = api_providers_file()
    raw = _load_json_file(path)
    if not isinstance(raw, list) or not raw:
        return 0
    set_setting("api_providers", raw, updated_at=now_ms())
    return len(raw)


def migrate_files_to_database(*, force: bool = False) -> dict[str, int]:
    if not force and is_migration_done():
        return {"skipped": 1}

    stats = {
        "projects": import_projects_from_files(),
        "canvases": import_canvases_from_files(),
        "conversations": import_conversations_from_files(),
        "providers": import_providers_from_files(),
    }
    mark_migration_done()
    return stats


def run_startup_migration() -> dict[str, int] | None:
    """Import JSON files when DB is empty or migration not yet marked."""
    if is_migration_done():
        return None
    has_files = bool(_canvas_dirs_to_scan() or _projects_file_candidates())
    providers_path = api_providers_file()
    if providers_path.is_file():
        has_files = True
    conv_root = conversations_dir()
    if conv_root.is_dir() and any(conv_root.iterdir()):
        has_files = True
    if not has_files:
        mark_migration_done()
        return None
    return migrate_files_to_database(force=False)
