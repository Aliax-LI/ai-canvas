"""Shared folders JSON storage — legacy parity (read-only LAN browse/import)."""

from __future__ import annotations

import json
import os
import urllib.parse
import uuid
from threading import Lock
from typing import Any

from fastapi import HTTPException

from infinite_canvas.core.asset_utils import content_type_for_path, sanitize_asset_name
from infinite_canvas.core.paths import app_data_dir, shared_folders_file
from infinite_canvas.core.websocket import now_ms
from infinite_canvas.services.asset_library_store import asset_library_media_kind

SHARED_MEDIA_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".mp4",
    ".webm",
    ".mov",
    ".m4v",
    ".mkv",
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".ogg",
    ".flac",
}
SHARED_SCAN_MAX_ENTRIES = 8000
SHARED_FOLDERS_LOCK = Lock()


def shared_folders_load() -> dict[str, Any]:
    path = shared_folders_file()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    folders = data.get("folders")
    if not isinstance(folders, list):
        folders = []
    return {"folders": [f for f in folders if isinstance(f, dict)]}


def shared_folders_save(data: dict[str, Any]) -> None:
    path = shared_folders_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def shared_folder_by_id(folder_id: str) -> dict[str, Any] | None:
    for entry in shared_folders_load().get("folders", []):
        if entry.get("id") == folder_id:
            return entry
    return None


def shared_folder_abs(entry: dict[str, Any] | None) -> str:
    rel = (entry or {}).get("rel") or ""
    return os.path.normpath(os.path.join(str(app_data_dir()), rel))


def shared_resolve_register(path: str) -> tuple[str, str]:
    """校验 path 必须位于 app_data_dir 内、是一个存在的子目录（非数据根）。"""
    raw = (path or "").strip().strip('"').strip("'")
    if not raw:
        raise HTTPException(status_code=400, detail="请提供文件夹路径")
    base = os.path.normpath(os.path.abspath(str(app_data_dir())))
    candidate = raw if os.path.isabs(raw) else os.path.join(base, raw)
    abs_path = os.path.normpath(os.path.abspath(candidate))
    try:
        common = os.path.commonpath([abs_path, base])
    except ValueError:
        raise HTTPException(status_code=400, detail="只允许登记数据目录内的文件夹")
    if common != base:
        raise HTTPException(status_code=400, detail="只允许登记数据目录内的文件夹")
    if abs_path == base:
        raise HTTPException(status_code=400, detail="不能直接登记数据根目录，请选择子文件夹")
    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=400, detail="文件夹不存在")
    rel = os.path.relpath(abs_path, base)
    return abs_path, rel


def shared_child_abs(folder_abs: str, rel: str) -> str:
    """把相对 folder_abs 的子路径解析为绝对路径，并防止越界访问。"""
    rel = (rel or "").replace("\\", "/").lstrip("/")
    abs_path = os.path.normpath(os.path.join(folder_abs, rel))
    base = os.path.normpath(os.path.abspath(folder_abs))
    try:
        common = os.path.commonpath([os.path.abspath(abs_path), base])
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径")
    if common != base:
        raise HTTPException(status_code=400, detail="非法路径")
    return abs_path


def scan_shared_tree(
    folder_id: str,
    folder_abs: str,
    rel_prefix: str = "",
    display: str = "",
    counter: dict[str, int] | None = None,
) -> dict[str, Any]:
    """递归扫描共享文件夹，返回 {id,name,path,items,children}。"""
    if counter is None:
        counter = {"n": 0}
    node: dict[str, Any] = {
        "id": f"{folder_id}:{rel_prefix or '__root__'}",
        "name": display or os.path.basename(folder_abs) or folder_abs,
        "path": rel_prefix,
        "items": [],
        "children": [],
    }
    try:
        entries = sorted(os.scandir(folder_abs), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError:
        return node
    for ent in entries:
        if counter["n"] >= SHARED_SCAN_MAX_ENTRIES:
            break
        if ent.name.startswith(".") or ent.name.startswith("._"):
            continue
        child_rel = f"{rel_prefix}/{ent.name}".lstrip("/")
        if ent.is_dir():
            child = scan_shared_tree(folder_id, ent.path, child_rel, ent.name, counter)
            if child["items"] or child["children"]:
                node["children"].append(child)
        elif ent.is_file():
            ext = os.path.splitext(ent.name)[1].lower()
            if ext not in SHARED_MEDIA_EXTS:
                continue
            counter["n"] += 1
            try:
                st = ent.stat()
                size = st.st_size
                mtime = int(st.st_mtime * 1000)
            except OSError:
                size = 0
                mtime = 0
            node["items"].append(
                {
                    "id": f"{folder_id}:{child_rel}",
                    "name": ent.name,
                    "url": f"/api/shared-folders/{folder_id}/file?path={urllib.parse.quote(child_rel)}",
                    "kind": asset_library_media_kind(ent.name),
                    "size": size,
                    "lastModified": mtime,
                    "relativePath": child_rel,
                    "folderId": folder_id,
                }
            )
    return node


def register_shared_folder(path: str, name: str = "") -> dict[str, Any]:
    abs_path, rel = shared_resolve_register(path)
    display_name = sanitize_asset_name(name or os.path.basename(abs_path), "共享文件夹")
    with SHARED_FOLDERS_LOCK:
        data = shared_folders_load()
        for entry in data.get("folders", []):
            if os.path.normpath(shared_folder_abs(entry)) == os.path.normpath(abs_path):
                entry["name"] = display_name
                shared_folders_save(data)
                return {**entry, "path": abs_path, "exists": True}
        entry = {
            "id": f"shared_{uuid.uuid4().hex[:12]}",
            "name": display_name,
            "rel": rel,
            "created_at": now_ms(),
        }
        data.setdefault("folders", []).append(entry)
        shared_folders_save(data)
    return {**entry, "path": abs_path, "exists": True}


def unregister_shared_folder(folder_id: str) -> None:
    with SHARED_FOLDERS_LOCK:
        data = shared_folders_load()
        before = len(data.get("folders", []))
        data["folders"] = [f for f in data.get("folders", []) if f.get("id") != folder_id]
        if len(data["folders"]) == before:
            raise HTTPException(status_code=404, detail="共享文件夹不存在")
        shared_folders_save(data)


def list_shared_folders_public() -> list[dict[str, Any]]:
    folders = []
    for entry in shared_folders_load().get("folders", []):
        abs_path = shared_folder_abs(entry)
        folders.append(
            {
                "id": entry.get("id"),
                "name": entry.get("name") or os.path.basename(abs_path) or abs_path,
                "rel": entry.get("rel") or "",
                "path": abs_path,
                "exists": os.path.isdir(abs_path),
                "created_at": entry.get("created_at"),
            }
        )
    return folders


def shared_folder_media_type(abs_path: str) -> str:
    return content_type_for_path(abs_path)
