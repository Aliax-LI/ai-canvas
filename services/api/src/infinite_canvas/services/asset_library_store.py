"""Asset library JSON storage — legacy parity (load/save/normalize)."""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

from infinite_canvas.core.asset_utils import sanitize_asset_name
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
