"""Asset library JSON storage — legacy parity (load/save/normalize)."""

from __future__ import annotations

import json
import os
import re
import shutil
import urllib.parse
import uuid
from pathlib import Path
from typing import Any

from infinite_canvas.core.asset_utils import sanitize_asset_name
from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.paths import asset_library_dir, asset_library_file
from infinite_canvas.core.websocket import now_ms

AVATAR_LEGACY_FLAT_FIELDS = (
    "platform",
    "provider_id",
    "project_name",
    "avatar_task_id",
    "avatar_status",
    "avatar_detail",
    "asset_uri",
    "asset_id",
    "registered_at",
)


def default_asset_library() -> dict[str, Any]:
    categories = [
        {"id": "characters", "name": "角色", "type": "image", "items": []},
        {"id": "scenes", "name": "场景", "type": "image", "items": []},
        {"id": "workflows", "name": "工作流", "type": "workflow", "items": []},
    ]
    return {
        "active_library_id": "default",
        "libraries": [{"id": "default", "name": "默认资产库", "type": "asset", "categories": categories}],
        "categories": categories,
        "updated_at": now_ms(),
    }


def migrate_asset_item_registrations(item: dict[str, Any]) -> None:
    if not isinstance(item, dict):
        return
    regs = item.get("registrations")
    if not isinstance(regs, dict):
        regs = {}
    legacy_platform = str(item.get("platform") or "").strip()
    if legacy_platform and legacy_platform not in regs and (item.get("asset_uri") or item.get("avatar_task_id")):
        regs[legacy_platform] = {
            "provider_id": item.get("provider_id") or "",
            "project_name": item.get("project_name") or "default",
            "task_id": item.get("avatar_task_id") or "",
            "status": item.get("avatar_status") or "",
            "detail": item.get("avatar_detail") or "",
            "asset_uri": item.get("asset_uri") or "",
            "asset_id": item.get("asset_id") or "",
            "registered_at": item.get("registered_at") or 0,
        }
    item["registrations"] = regs if isinstance(regs, dict) else {}
    for key in AVATAR_LEGACY_FLAT_FIELDS:
        item.pop(key, None)


def sort_asset_library_items(lib: dict[str, Any]) -> None:
    cats: list[dict[str, Any]] = list(lib.get("categories", []))
    for library in lib.get("libraries", []) if isinstance(lib.get("libraries"), list) else []:
        cats.extend(library.get("categories") or [])
    seen: set[int] = set()
    for cat in cats:
        if id(cat) in seen:
            continue
        seen.add(id(cat))
        items = cat.get("items")
        if isinstance(items, list):

            def created_at_key(item: object) -> int:
                if not isinstance(item, dict):
                    return 0
                try:
                    return int(float(item.get("created_at") or 0))
                except (TypeError, ValueError):
                    return 0

            items.sort(key=created_at_key, reverse=True)


def normalize_asset_library(lib: object) -> dict[str, Any]:
    if not isinstance(lib, dict):
        lib = default_asset_library()
    legacy_categories = lib.get("categories") if isinstance(lib.get("categories"), list) else None
    libraries = lib.get("libraries") if isinstance(lib.get("libraries"), list) else []
    if not libraries:
        libraries = [
            {
                "id": "default",
                "name": "默认资产库",
                "type": "asset",
                "categories": legacy_categories or default_asset_library()["categories"],
            }
        ]
    for library in libraries:
        library["id"] = re.sub(r"[^A-Za-z0-9_-]+", "_", str(library.get("id") or f"lib_{uuid.uuid4().hex[:8]}"))[:40]
        library["name"] = sanitize_asset_name(library.get("name") or "资产库", "资产库")
        cats = library.get("categories") if isinstance(library.get("categories"), list) else []
        if library.get("id") == "default" and not any(c.get("type") == "workflow" for c in cats):
            cats.append({"id": "workflows", "name": "工作流", "type": "workflow", "items": []})
        for cat in cats:
            for item in cat.get("items") or []:
                migrate_asset_item_registrations(item)
        library["categories"] = cats
    active = str(lib.get("active_library_id") or libraries[0].get("id") or "default")
    if not any(item.get("id") == active for item in libraries):
        active = libraries[0].get("id") or "default"
    active_library = next((item for item in libraries if item.get("id") == active), libraries[0])
    lib = dict(lib)
    lib["libraries"] = libraries
    lib["active_library_id"] = active
    lib["categories"] = active_library.get("categories") or []
    lib["updated_at"] = int(lib.get("updated_at") or now_ms())
    sort_asset_library_items(lib)
    return lib


def load_asset_library() -> dict[str, Any]:
    path = asset_library_file()
    asset_library_dir().mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        lib = default_asset_library()
        save_asset_library(lib)
        return lib
    try:
        with open(path, encoding="utf-8") as f:
            lib = json.load(f)
    except Exception:
        lib = default_asset_library()
    return normalize_asset_library(lib)


def save_asset_library(lib: dict[str, Any]) -> dict[str, Any]:
    lib = normalize_asset_library(lib)
    path = asset_library_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    return lib


def asset_library_media_kind(path: str, content_type: str = "") -> str:
    ext = os.path.splitext(path or "")[1].lower()
    ct = (content_type or "").lower()
    if ext in {".json", ".zip"}:
        return "workflow"
    if ext in {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"} or ct.startswith("video/"):
        return "video"
    if ext in {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"} or ct.startswith("audio/"):
        return "audio"
    return "image"


def asset_library_safe_extension(path: str, kind: str) -> str:
    ext = os.path.splitext(path or "")[1].lower()
    allowed = {
        "image": {".png", ".jpg", ".jpeg", ".webp", ".gif"},
        "video": {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"},
        "audio": {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"},
        "workflow": {".json", ".zip"},
    }
    fallback = {"image": ".png", "video": ".mp4", "audio": ".mp3", "workflow": ".zip"}
    return ext if ext in allowed.get(kind, allowed["image"]) else fallback.get(kind, ".png")


def unique_asset_category_dir(library: dict[str, Any], base_name: str) -> str:
    """为资产库分组生成唯一、文件系统安全的子文件夹名（library/<dir>/）。"""
    base = sanitize_asset_name(base_name, "分组").strip(" .") or "分组"
    lib_dir = asset_library_dir()
    existing = {
        str(c.get("dir"))
        for c in (library.get("categories") or [])
        if isinstance(c, dict) and c.get("dir")
    }
    candidate = base
    i = 2
    while candidate in existing or (lib_dir / candidate).exists():
        candidate = f"{base}_{i}"
        i += 1
    return candidate


def remove_asset_library_file(item: object) -> None:
    """删除资产对应的本地文件（仅限 library 副本）。"""
    try:
        url = item.get("url") if isinstance(item, dict) else ""
        path = output_file_from_url(url)
        if path and path.is_file():
            path.unlink()
    except Exception as exc:
        print(f"删除资产文件失败: {exc}")


def make_asset_library_item(src: str | Path, name: str = "", subdir: str = "") -> tuple[str, dict[str, Any]]:
    src_path = Path(src)
    kind = asset_library_media_kind(str(src_path))
    ext = asset_library_safe_extension(str(src_path), kind)
    safe_name = sanitize_asset_name(name or src_path.name, "asset")
    if not os.path.splitext(safe_name)[1]:
        safe_name += ext
    dest_name = f"lib_{uuid.uuid4().hex[:12]}_{safe_name}"
    lib_dir = asset_library_dir()
    subdir = str(subdir or "").strip("/").strip()
    if subdir:
        dest_dir = lib_dir / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / dest_name
        rel = f"{subdir}/{dest_name}"
    else:
        dest_path = lib_dir / dest_name
        rel = dest_name
    shutil.copy2(src_path, dest_path)
    item = {
        "id": f"asset_{uuid.uuid4().hex[:12]}",
        "name": os.path.splitext(safe_name)[0][:120],
        "url": "/assets/library/" + urllib.parse.quote(rel, safe="/"),
        "kind": kind,
        "created_at": now_ms(),
    }
    return dest_name, item


def find_asset_library(lib: dict[str, Any], library_id: str = "") -> dict[str, Any] | None:
    lib = normalize_asset_library(lib)
    library_id = str(library_id or lib.get("active_library_id") or "").strip()
    return next((item for item in lib.get("libraries", []) if item.get("id") == library_id), None) or (
        (lib.get("libraries") or [None])[0]
    )


def find_asset_category_in_library(
    lib: dict[str, Any], category_id: str, library_id: str = ""
) -> dict[str, Any] | None:
    library = find_asset_library(lib, library_id)
    if not library:
        return None
    for cat in library.get("categories", []):
        if cat.get("id") == category_id:
            return cat
    return None


def find_asset_category_with_library(
    lib: dict[str, Any], category_id: str, library_id: str = ""
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    lib = normalize_asset_library(lib)
    preferred = str(library_id or "").strip()
    libraries = lib.get("libraries", []) or []
    if preferred:
        libraries = [item for item in libraries if item.get("id") == preferred]
    for library in libraries:
        for cat in library.get("categories", []) or []:
            if cat.get("id") == category_id:
                return library, cat
    return None, None


def find_asset_item_in_library(
    lib: dict[str, Any], item_id: str, library_id: str = ""
) -> dict[str, Any] | None:
    for library in lib.get("libraries", []):
        if library_id and library.get("id") != library_id:
            continue
        for cat in library.get("categories", []):
            for item in cat.get("items", []):
                if item.get("id") == item_id:
                    return item
    return None


def asset_library_workflow_category(
    lib: dict[str, Any], library_id: str = "", category_id: str = ""
) -> tuple[dict[str, Any], dict[str, Any]]:
    from fastapi import HTTPException

    library = find_asset_library(lib, library_id)
    if not library:
        raise HTTPException(status_code=404, detail="资产库不存在")
    categories: list[dict[str, Any]] = library.setdefault("categories", [])
    cat: dict[str, Any] | None = None
    if category_id:
        cat = next((c for c in categories if c.get("id") == category_id), None)
        if not cat:
            raise HTTPException(status_code=404, detail="工作流分类不存在")
        if cat.get("type") != "workflow":
            raise HTTPException(status_code=400, detail="目标分组不是工作流分类")
    if not cat:
        cat = next((c for c in categories if c.get("type") == "workflow"), None)
    if not cat:
        cat = {"id": f"wf_{uuid.uuid4().hex[:12]}", "name": "工作流", "type": "workflow", "items": []}
        categories.append(cat)
    lib["active_library_id"] = library.get("id") or lib.get("active_library_id")
    return library, cat


def make_workflow_library_item_from_bytes(raw: bytes, filename: str, name: str = "") -> dict[str, Any]:
    from fastapi import HTTPException

    from infinite_canvas.core.media import sanitize_export_filename

    if not raw:
        raise HTTPException(status_code=400, detail="工作流文件为空")
    safe_filename = sanitize_export_filename(filename or "canvas-workflow.zip", "canvas-workflow.zip")
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in {".json", ".zip"}:
        safe_filename += ".zip"
        ext = ".zip"
    dest_name = f"workflow_{uuid.uuid4().hex[:12]}_{safe_filename}"
    lib_dir = asset_library_dir()
    lib_dir.mkdir(parents=True, exist_ok=True)
    dest_path = lib_dir / dest_name
    dest_path.write_bytes(raw)
    display_name = sanitize_asset_name(name or os.path.splitext(safe_filename)[0], "工作流")
    return {
        "id": f"wf_{uuid.uuid4().hex[:12]}",
        "name": display_name[:120],
        "url": f"/assets/library/{dest_name}",
        "kind": "workflow",
        "type": "workflow",
        "format": "zip" if ext == ".zip" else "json",
        "size": len(raw),
        "created_at": now_ms(),
    }
