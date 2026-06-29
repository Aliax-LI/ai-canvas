"""Prompt library JSON storage — legacy parity (load/save/normalize)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from infinite_canvas.core.asset_utils import sanitize_asset_name
from infinite_canvas.core.paths import prompt_libraries_file
from infinite_canvas.core.websocket import now_ms


def default_prompt_template_categories() -> list[dict[str, str]]:
    return [
        {"id": "view", "name": "视角"},
        {"id": "storyboard", "name": "分镜"},
        {"id": "character", "name": "角色"},
        {"id": "product", "name": "产品"},
        {"id": "lighting", "name": "光影"},
        {"id": "custom", "name": "我的"},
    ]


def normalize_prompt_category_id(category: str = "custom") -> str:
    category_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(category or "custom"))[:40] or "custom"
    return "custom" if category_id in {"mine", "my", "personal"} else category_id


def normalize_prompt_library_item(item: object) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    name = sanitize_asset_name(item.get("name") or "提示词", "提示词")
    positive = str(item.get("positive") or item.get("text") or "").strip()
    return {
        "id": re.sub(
            r"[^A-Za-z0-9_-]+",
            "_",
            str(item.get("id") or item.get("item_id") or f"tpl_{uuid.uuid4().hex[:12]}"),
        )[:60],
        "name": name,
        "category": normalize_prompt_category_id(item.get("category") or "custom"),
        "scene": str(item.get("scene") or "").strip()[:500],
        "positive": positive,
        "negative": str(item.get("negative") or "").strip(),
        "params": item.get("params") if isinstance(item.get("params"), dict) else {},
        "created_at": int(item.get("created_at") or now_ms()),
        "updated_at": int(item.get("updated_at") or item.get("created_at") or now_ms()),
    }


def seed_system_prompt_library() -> dict[str, Any]:
    return {
        "id": "system",
        "name": "系统提示词库",
        "type": "prompt",
        "items": [],
        "categories": default_prompt_template_categories(),
    }


def default_prompt_libraries() -> dict[str, Any]:
    return {
        "active_library_id": "system",
        "libraries": [seed_system_prompt_library()],
        "updated_at": now_ms(),
    }


def normalize_prompt_template_categories(*category_lists: object, include_defaults: bool = True) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()

    def add_category(category: object) -> None:
        if not isinstance(category, dict):
            return
        cat_id = normalize_prompt_category_id(category.get("id") or category.get("name") or "custom")
        if cat_id in seen:
            return
        seen.add(cat_id)
        name = sanitize_asset_name(category.get("name") or cat_id, cat_id)
        normalized.append({"id": cat_id, "name": name})

    for categories in category_lists:
        if isinstance(categories, list):
            for category in categories:
                add_category(category)
    if include_defaults and not normalized:
        for category in default_prompt_template_categories():
            add_category(category)
    return normalized


def normalize_prompt_libraries(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = default_prompt_libraries()
    raw_libraries = data.get("libraries") if isinstance(data.get("libraries"), list) else []
    raw_libraries = [lib for lib in raw_libraries if isinstance(lib, dict)]
    if not any(lib.get("id") == "system" for lib in raw_libraries):
        raw_libraries = [seed_system_prompt_library()] + raw_libraries
    libraries: list[dict[str, Any]] = []
    seen_lib_ids: set[str] = set()
    for raw in raw_libraries:
        is_system = raw.get("id") == "system"
        if is_system:
            lib_id = "system"
        else:
            lib_id = (
                re.sub(r"[^A-Za-z0-9_-]+", "_", str(raw.get("id") or f"lib_{uuid.uuid4().hex[:12]}"))[:60]
                or f"lib_{uuid.uuid4().hex[:12]}"
            )
        if lib_id in seen_lib_ids:
            continue
        seen_lib_ids.add(lib_id)
        items: list[dict[str, Any]] = []
        seen_items: set[str] = set()
        for raw_item in raw.get("items") if isinstance(raw.get("items"), list) else []:
            if not isinstance(raw_item, dict):
                continue
            item = normalize_prompt_library_item(raw_item)
            item_id = item.get("id") or f"tpl_{uuid.uuid4().hex[:12]}"
            if item_id in seen_items:
                continue
            seen_items.add(item_id)
            items.append(item)
        default_name = "系统提示词库" if is_system else "提示词库"
        raw_categories = raw.get("categories") if isinstance(raw.get("categories"), list) else []
        if not is_system:
            builtin_ids = {"view", "storyboard", "character", "product", "lighting", "custom"}
            raw_categories = [
                c
                for c in raw_categories
                if isinstance(c, dict)
                and normalize_prompt_category_id(c.get("id") or c.get("name") or "") not in builtin_ids
            ]
        libraries.append(
            {
                "id": lib_id,
                "name": sanitize_asset_name(raw.get("name") or default_name, default_name),
                "type": "prompt",
                "readonly": False,
                "system": is_system,
                "categories": normalize_prompt_template_categories(raw_categories, include_defaults=is_system),
                "items": items,
            }
        )
    active = str(data.get("active_library_id") or "system")
    if not any(lib["id"] == active for lib in libraries):
        active = "system" if any(lib["id"] == "system" for lib in libraries) else (libraries[0]["id"] if libraries else "system")
    return {
        "active_library_id": active,
        "libraries": libraries,
        "updated_at": int(data.get("updated_at") or now_ms()),
    }


def load_prompt_libraries() -> dict[str, Any]:
    path = prompt_libraries_file()
    if not path.is_file():
        data = default_prompt_libraries()
        return save_prompt_libraries(data)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = default_prompt_libraries()
    if not isinstance(data, dict):
        data = default_prompt_libraries()
    normalized = normalize_prompt_libraries(data)
    if normalized.get("active_library_id") != data.get("active_library_id") or normalized.get("libraries") != data.get(
        "libraries"
    ):
        return save_prompt_libraries(normalized)
    return normalized


def save_prompt_libraries(data: dict[str, Any]) -> dict[str, Any]:
    data = normalize_prompt_libraries(data)
    data["updated_at"] = now_ms()
    path = prompt_libraries_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def find_prompt_library(data: object, library_id: str = "") -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    libraries = data.get("libraries") if isinstance(data.get("libraries"), list) else []
    library_id = str(library_id or data.get("active_library_id") or "").strip()
    return next((item for item in libraries if item.get("id") == library_id), None) or (
        libraries[0] if libraries else None
    )


def public_prompt_libraries(data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = normalize_prompt_libraries(data or load_prompt_libraries())
    return {
        "active_library_id": data.get("active_library_id")
        or (data.get("libraries") or [{}])[0].get("id")
        or "system",
        "libraries": data.get("libraries") or [],
        "updated_at": data.get("updated_at") or now_ms(),
    }
