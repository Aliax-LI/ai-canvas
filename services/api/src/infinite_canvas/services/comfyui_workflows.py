"""ComfyUI workflow storage and path helpers — legacy parity."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from infinite_canvas.core.paths import legacy_workflows_dir, workflows_dir

BUILTIN_WORKFLOWS = {
    "Z-Image.json",
    "Z-Image-Enhance.json",
    "2511.json",
    "klein-enhance.json",
    "Flux2-Klein.json",
    "upscale.json",
}
CUSTOM_WORKFLOW_FOLDER = "custom"
LEGACY_CUSTOM_WORKFLOW_FOLDER = "自定义"
WORKFLOW_NAME_RE = re.compile(
    rf"^(?:(?:{CUSTOM_WORKFLOW_FOLDER}|{LEGACY_CUSTOM_WORKFLOW_FOLDER})/)?[a-zA-Z0-9_一-龥\.\-]+\.json$"
)


def workflow_roots() -> list[Path]:
    roots: list[Path] = []
    primary = workflows_dir()
    if primary.is_dir():
        roots.append(primary)
    legacy = legacy_workflows_dir()
    if legacy.is_dir() and legacy not in roots:
        roots.append(legacy)
    return roots or [primary]


def is_builtin_workflow(name: str) -> bool:
    return "/" not in name and os.path.basename(name) in BUILTIN_WORKFLOWS


def workflow_path_from_name(name: str) -> Path:
    if not WORKFLOW_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid workflow name")
    for root in workflow_roots():
        path = (root / Path(*name.split("/"))).resolve()
        root_resolved = root.resolve()
        try:
            path.relative_to(root_resolved)
        except ValueError:
            continue
        if path.is_file():
            return path
    # Return primary path for write operations even when missing.
    primary = workflows_dir()
    path = (primary / Path(*name.split("/"))).resolve()
    root_resolved = primary.resolve()
    if os.path.commonpath([str(root_resolved), str(path)]) != str(root_resolved):
        raise HTTPException(status_code=400, detail="Invalid workflow name")
    return path


def workflow_config_path(name: str) -> Path:
    return workflow_path_from_name(name).with_suffix(".config.json")


def list_workflows() -> dict[str, list[dict[str, Any]]]:
    root = workflows_dir()
    if not root.is_dir():
        return {"workflows": []}
    items: list[dict[str, Any]] = []
    for walk_root, dirs, files in os.walk(root):
        if os.path.abspath(walk_root) == os.path.abspath(root):
            dirs[:] = [d for d in dirs if d in {CUSTOM_WORKFLOW_FOLDER, LEGACY_CUSTOM_WORKFLOW_FOLDER}]
        for fn in sorted(files):
            if not fn.endswith(".json") or fn.endswith(".config.json"):
                continue
            rel = os.path.relpath(os.path.join(walk_root, fn), root).replace("\\", "/")
            if is_builtin_workflow(rel):
                continue
            cfg: dict[str, Any] = {}
            cfg_path = workflow_config_path(rel)
            if cfg_path.is_file():
                try:
                    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) or {}
                except Exception:
                    cfg = {}
            items.append(
                {
                    "name": rel,
                    "title": cfg.get("title") or fn.replace(".json", ""),
                    "builtin": False,
                    "field_count": len(cfg.get("fields") or []),
                }
            )
    items.sort(
        key=lambda item: (0 if item["name"].startswith(f"{CUSTOM_WORKFLOW_FOLDER}/") else 1, item["title"])
    )
    return {"workflows": items}


def get_workflow(name: str) -> dict[str, Any]:
    if not WORKFLOW_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid workflow name")
    workflow_path = workflow_path_from_name(name)
    if not workflow_path.is_file():
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    cfg: dict[str, Any] = {"title": name.replace(".json", ""), "fields": []}
    cfg_path = workflow_config_path(name)
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8")) or cfg
        except Exception:
            pass
    return {
        "name": name,
        "workflow": workflow,
        "config": cfg,
        "builtin": is_builtin_workflow(name),
    }


def upload_workflow(payload_name: str, workflow: dict[str, Any]) -> dict[str, str]:
    name = os.path.basename(payload_name.strip())
    if not name.endswith(".json"):
        name = name + ".json"
    if not WORKFLOW_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="工作流名称不合法，请使用中文/英文/数字/_-.")
    if not isinstance(workflow, dict) or not workflow:
        raise HTTPException(status_code=400, detail="工作流 JSON 为空")
    sample = next(iter(workflow.values()), None)
    if not isinstance(sample, dict) or "class_type" not in sample:
        raise HTTPException(status_code=400, detail="不是有效的 ComfyUI API 工作流 JSON（需包含 class_type）")
    custom_dir = workflows_dir() / CUSTOM_WORKFLOW_FOLDER
    custom_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{CUSTOM_WORKFLOW_FOLDER}/{name}"
    path = workflow_path_from_name(stored_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"name": stored_name}


def save_workflow_config(name: str, config: dict[str, Any]) -> dict[str, Any]:
    if not WORKFLOW_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid workflow name")
    workflow_path = workflow_path_from_name(name)
    if not workflow_path.is_file():
        raise HTTPException(status_code=404, detail="Workflow not found")
    cfg_path = workflow_config_path(name)
    cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"config": config}


def delete_workflow(name: str) -> dict[str, bool]:
    if not WORKFLOW_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid workflow name")
    if is_builtin_workflow(name):
        raise HTTPException(status_code=400, detail="内置工作流不可删除")
    workflow_path = workflow_path_from_name(name)
    cfg_path = workflow_config_path(name)
    if not workflow_path.is_file():
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow_path.unlink()
    if cfg_path.is_file():
        cfg_path.unlink()
    return {"ok": True}


def resolve_workflow_file(name: str) -> Path:
    """Resolve workflow JSON path for generate (app data + builtin fallback)."""
    path = workflow_path_from_name(name)
    if path.is_file():
        return path
    if name == "Z-Image.json":
        legacy = legacy_workflows_dir() / "Z-Image.json"
        if legacy.is_file():
            return legacy
    raise FileNotFoundError(f"Workflow file not found: {name}")
