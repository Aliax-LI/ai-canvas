"""Canvas storage, listing, and CRUD — migrated from legacy main.py."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import HTTPException

from infinite_canvas.core.database import (
    delete_canvas_row,
    get_canvas,
    list_canvas_rows,
    move_canvases_project as db_move_canvases_project,
    purge_expired_trash,
    upsert_canvas,
    use_sqlite_storage,
)
from infinite_canvas.core.paths import canvases_dir, legacy_canvases_dir
from infinite_canvas.core.websocket import manager, now_ms

CANVAS_TRASH_RETENTION_MS = 30 * 24 * 60 * 60 * 1000
CANVAS_LOCK = Lock()
DEFAULT_PROJECT_ID = "default"

CANVAS_COLORS = {"", "red", "orange", "amber", "green", "teal", "blue", "violet", "pink", "slate"}


def _primary_canvases_dir() -> Path:
    return canvases_dir()


def _legacy_canvases_dir() -> Path:
    return legacy_canvases_dir()


def _dir_has_canvases(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    return any(f.suffix == ".json" for f in directory.iterdir())


def canvases_dir_for_read() -> Path:
    primary = _primary_canvases_dir()
    if _dir_has_canvases(primary):
        return primary
    legacy = _legacy_canvases_dir()
    if _dir_has_canvases(legacy):
        return legacy
    return primary


def canvases_dir_for_write() -> Path:
    primary = _primary_canvases_dir()
    if _dir_has_canvases(primary):
        return primary
    legacy = _legacy_canvases_dir()
    if _dir_has_canvases(legacy):
        return legacy
    return primary


def canvas_path(canvas_id: str) -> Path:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", canvas_id or "")
    if not cleaned:
        raise HTTPException(status_code=400, detail="无效的画布 ID")
    return canvases_dir_for_write() / f"{cleaned}.json"


def normalize_canvas_kind(kind: str = "classic") -> str:
    return "smart" if str(kind or "").strip().lower() == "smart" else "classic"


def normalize_canvas_color(value: Any) -> str:
    color = str(value or "").strip().lower()
    return color if color in CANVAS_COLORS else ""


def save_canvas(canvas: dict[str, Any]) -> None:
    canvas["updated_at"] = now_ms()
    if use_sqlite_storage():
        with CANVAS_LOCK:
            upsert_canvas(canvas)
        return
    path = canvas_path(canvas["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with CANVAS_LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(canvas, f, ensure_ascii=False, indent=2)


def canvas_record(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": data.get("id"),
        "title": data.get("title", "未命名画布"),
        "icon": data.get("icon", "🧩"),
        "kind": normalize_canvas_kind(data.get("kind")),
        "owner": str(data.get("owner") or "")[:40],
        "color": normalize_canvas_color(data.get("color")),
        "pinned": bool(data.get("pinned") or False),
        "project": str(data.get("project") or "").strip() or DEFAULT_PROJECT_ID,
        "board_x": data.get("board_x"),
        "board_y": data.get("board_y"),
        "created_at": data.get("created_at", 0),
        "updated_at": data.get("updated_at", 0),
        "deleted_at": data.get("deleted_at", 0),
        "node_count": len(data.get("nodes", [])),
    }


def new_canvas(
    title: str = "未命名画布",
    icon: str = "layers",
    kind: str = "classic",
    project: str | None = None,
    board_x: float | None = None,
    board_y: float | None = None,
) -> dict[str, Any]:
    timestamp = now_ms()
    canvas_kind = normalize_canvas_kind(kind)
    canvas: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "title": (title or ("智能画布" if canvas_kind == "smart" else "未命名画布"))[:80],
        "icon": (icon or ("sparkles" if canvas_kind == "smart" else "🧩"))[:32],
        "kind": canvas_kind,
        "owner": "",
        "color": "",
        "pinned": False,
        "project": str(project or "").strip() or DEFAULT_PROJECT_ID,
        "created_at": timestamp,
        "updated_at": timestamp,
        "nodes": [],
        "connections": [],
        "viewport": {"x": 0, "y": 0, "scale": 1},
    }
    if board_x is not None:
        canvas["board_x"] = float(board_x)
    if board_y is not None:
        canvas["board_y"] = float(board_y)
    save_canvas(canvas)
    return canvas


def load_canvas(canvas_id: str) -> dict[str, Any]:
    canvas = load_canvas_any(canvas_id)
    if canvas.get("deleted_at"):
        raise HTTPException(status_code=404, detail="画布已在回收站")
    return canvas


def load_canvas_any(canvas_id: str) -> dict[str, Any]:
    if use_sqlite_storage():
        canvas = get_canvas(canvas_id)
        if canvas is None:
            raise HTTPException(status_code=404, detail="画布不存在")
        return canvas
    path = canvas_path(canvas_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="画布不存在")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def cleanup_expired_canvas_trash() -> None:
    cutoff = now_ms() - CANVAS_TRASH_RETENTION_MS
    if use_sqlite_storage():
        purge_expired_trash(cutoff)
        return
    directory = canvases_dir_for_read()
    if not directory.is_dir():
        return
    with CANVAS_LOCK:
        for filename in directory.iterdir():
            if filename.suffix != ".json":
                continue
            try:
                with open(filename, encoding="utf-8") as f:
                    data = json.load(f)
                deleted_at = int(data.get("deleted_at") or 0)
                if deleted_at and deleted_at < cutoff:
                    filename.unlink()
            except Exception:
                continue


def iter_canvas_records(include_deleted: bool = False) -> list[dict[str, Any]]:
    cleanup_expired_canvas_trash()
    if use_sqlite_storage():
        docs = list_canvas_rows(include_deleted=include_deleted)
        return [canvas_record(doc) for doc in docs]
    records: list[dict[str, Any]] = []
    directory = canvases_dir_for_read()
    if not directory.is_dir():
        return records
    for filepath in directory.iterdir():
        if filepath.suffix != ".json":
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        is_deleted = bool(data.get("deleted_at"))
        if include_deleted != is_deleted:
            continue
        records.append(canvas_record(data))
    return records


def list_canvases() -> list[dict[str, Any]]:
    records = iter_canvas_records(include_deleted=False)
    return sorted(
        records,
        key=lambda item: (
            0 if item.get("pinned") else 1,
            -int(item.get("updated_at") or item.get("created_at") or 0),
        ),
    )


def list_deleted_canvases() -> list[dict[str, Any]]:
    records = iter_canvas_records(include_deleted=True)
    return sorted(records, key=lambda item: item["deleted_at"], reverse=True)


def move_canvases_to_project(from_project: str, to_project: str) -> int:
    if use_sqlite_storage():
        return db_move_canvases_project(from_project, to_project)
    moved = 0
    directory = canvases_dir_for_read()
    if not directory.is_dir():
        return moved
    with CANVAS_LOCK:
        for filepath in directory.iterdir():
            if filepath.suffix != ".json":
                continue
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if str(data.get("project") or "") == from_project:
                data["project"] = to_project
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                moved += 1
    return moved


def update_canvas_meta(canvas_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    canvas = load_canvas(canvas_id)
    if updates.get("title") is not None:
        canvas["title"] = (updates["title"] or canvas.get("title") or "未命名画布")[:80]
    if updates.get("icon") is not None:
        canvas["icon"] = (updates["icon"] or "layers")[:32]
    if updates.get("owner") is not None:
        canvas["owner"] = str(updates["owner"]).strip()[:40]
    if updates.get("color") is not None:
        canvas["color"] = normalize_canvas_color(updates["color"])
    if updates.get("pinned") is not None:
        canvas["pinned"] = bool(updates["pinned"])
    if updates.get("project") is not None:
        canvas["project"] = str(updates["project"]).strip() or DEFAULT_PROJECT_ID
    if updates.get("board_x") is not None:
        canvas["board_x"] = float(updates["board_x"])
    if updates.get("board_y") is not None:
        canvas["board_y"] = float(updates["board_y"])
    canvas["updated_at"] = now_ms()
    save_canvas(canvas)
    return canvas_record(canvas)


async def update_canvas(canvas_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    canvas = load_canvas(canvas_id)
    current_updated_at = int(canvas.get("updated_at") or 0)
    base_updated_at = int(payload.get("base_updated_at") or 0)
    if base_updated_at and current_updated_at and base_updated_at < current_updated_at:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "画布已被其他页面更新，已拒绝旧版本覆盖。",
                "canvas": canvas,
                "updated_at": current_updated_at,
            },
        )
    canvas["title"] = (payload.get("title") or canvas.get("title") or "未命名画布")[:80]
    canvas["icon"] = (payload.get("icon") or canvas.get("icon") or "layers")[:32]
    canvas["kind"] = normalize_canvas_kind(canvas.get("kind"))
    canvas["nodes"] = payload.get("nodes", [])
    canvas["connections"] = payload.get("connections", [])
    if canvas["kind"] == "smart":
        canvas["viewport"] = payload.get("viewport", {})
    else:
        canvas["viewport"] = canvas.get("viewport") or {"x": 0, "y": 0, "scale": 1}
    logs = payload.get("logs", [])
    canvas["logs"] = logs[-500:]
    canvas["settings"] = payload.get("settings") or {}
    save_canvas(canvas)
    await manager.broadcast_canvas_updated(
        canvas_id, int(canvas.get("updated_at") or now_ms()), payload.get("client_id", "")
    )
    return canvas


def delete_canvas(canvas_id: str) -> dict[str, bool]:
    canvas = load_canvas_any(canvas_id)
    if not canvas.get("deleted_at"):
        canvas["deleted_at"] = now_ms()
        save_canvas(canvas)
    return {"ok": True}


def restore_canvas(canvas_id: str) -> dict[str, Any]:
    canvas = load_canvas_any(canvas_id)
    if canvas.get("deleted_at"):
        canvas.pop("deleted_at", None)
        save_canvas(canvas)
    return canvas


def purge_canvas(canvas_id: str) -> dict[str, bool]:
    if use_sqlite_storage():
        delete_canvas_row(canvas_id)
        return {"ok": True}
    path = canvas_path(canvas_id)
    if path.is_file():
        path.unlink()
    return {"ok": True}
