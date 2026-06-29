"""Project list and CRUD — migrated from legacy main.py."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from infinite_canvas.core.database import (
    load_projects_rows,
    save_projects_batch,
    use_sqlite_storage,
)
from infinite_canvas.core.paths import legacy_projects_file, projects_file
from infinite_canvas.core.websocket import now_ms
from infinite_canvas.services import canvas_store

DEFAULT_PROJECT_ID = "default"
PROJECTS_LOCK = canvas_store.CANVAS_LOCK


def _primary_projects_file() -> Path:
    return projects_file()


def _legacy_projects_file() -> Path:
    return legacy_projects_file()


def projects_file_for_read() -> Path | None:
    primary = _primary_projects_file()
    if primary.is_file():
        return primary
    legacy = _legacy_projects_file()
    if legacy.is_file():
        return legacy
    return None


def projects_file_for_write() -> Path:
    primary = _primary_projects_file()
    if primary.is_file():
        return primary
    legacy = _legacy_projects_file()
    if legacy.is_file():
        return legacy
    return primary


def load_projects() -> list[dict[str, Any]]:
    if use_sqlite_storage():
        return load_projects_rows()
    path = projects_file_for_read()
    if path is None:
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        projects = data.get("projects") if isinstance(data, dict) else data
        if isinstance(projects, list):
            return [p for p in projects if isinstance(p, dict) and p.get("id")]
    except Exception:
        pass
    return []


def save_projects(projects: list[dict[str, Any]]) -> None:
    if use_sqlite_storage():
        with PROJECTS_LOCK:
            save_projects_batch(projects)
        return
    write_path = projects_file_for_write()
    write_path.parent.mkdir(parents=True, exist_ok=True)
    with PROJECTS_LOCK:
        with open(write_path, "w", encoding="utf-8") as f:
            json.dump({"projects": projects}, f, ensure_ascii=False, indent=2)


def project_record(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": project.get("id"),
        "name": (project.get("name") or "未命名项目")[:60],
        "order": int(project.get("order") or 0),
        "created_at": project.get("created_at", 0),
        "updated_at": project.get("updated_at", 0),
    }


def ensure_default_project() -> list[dict[str, Any]]:
    projects = load_projects()
    changed = False
    if not any(p.get("id") == DEFAULT_PROJECT_ID for p in projects):
        ts = now_ms()
        projects.insert(
            0,
            {
                "id": DEFAULT_PROJECT_ID,
                "name": "默认项目",
                "order": 0,
                "created_at": ts,
                "updated_at": ts,
            },
        )
        changed = True
    if changed:
        save_projects(projects)
    return projects


def new_project(name: str = "新项目") -> dict[str, Any]:
    projects = ensure_default_project()
    ts = now_ms()
    clean = (str(name or "").strip() or "新项目")[:60]
    order = max([int(p.get("order") or 0) for p in projects], default=0) + 1
    proj = {
        "id": uuid.uuid4().hex,
        "name": clean,
        "order": order,
        "created_at": ts,
        "updated_at": ts,
    }
    projects.append(proj)
    save_projects(projects)
    return proj


def list_projects() -> list[dict[str, Any]]:
    projects = ensure_default_project()
    counts: dict[str, int] = {}
    for rec in canvas_store.iter_canvas_records(include_deleted=False):
        pid = rec.get("project") or DEFAULT_PROJECT_ID
        counts[pid] = counts.get(pid, 0) + 1
    out: list[dict[str, Any]] = []
    for p in sorted(projects, key=lambda x: (int(x.get("order") or 0), x.get("created_at") or 0)):
        rec = project_record(p)
        rec["canvas_count"] = counts.get(rec["id"], 0)
        out.append(rec)
    return out


def update_project(
    project_id: str, name: str | None = None, order: int | None = None
) -> dict[str, Any]:
    projects = ensure_default_project()
    target = next((p for p in projects if p.get("id") == project_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="项目不存在")
    if name is not None:
        target["name"] = (str(name).strip() or target.get("name") or "未命名项目")[:60]
    if order is not None:
        target["order"] = int(order)
    target["updated_at"] = now_ms()
    save_projects(projects)
    return project_record(target)


def delete_project(project_id: str) -> dict[str, Any]:
    if project_id == DEFAULT_PROJECT_ID:
        raise HTTPException(status_code=400, detail="默认项目不可删除")
    projects = ensure_default_project()
    if not any(p.get("id") == project_id for p in projects):
        raise HTTPException(status_code=404, detail="项目不存在")
    projects = [p for p in projects if p.get("id") != project_id]
    save_projects(projects)
    moved = canvas_store.move_canvases_to_project(project_id, DEFAULT_PROJECT_ID)
    return {"ok": True, "moved": moved}
