"""Repository and user data path resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def repo_root() -> Path:
    """Monorepo root (ai-canvas/)."""
    return Path(__file__).resolve().parents[5]


def coding_root() -> Path:
    """Upstream Infinite-Canvas tree (gitignored, local only)."""
    override = os.getenv("INFINITE_CANVAS_CODING_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "coding" / "Infinite-Canvas"


def app_data_dir() -> Path:
    """Per-user writable data directory."""
    override = os.getenv("INFINITE_CANVAS_DATA", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = os.getenv("APPDATA", str(Path.home()))
        return Path(base) / "infinite-canvas"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "infinite-canvas"
    return Path.home() / ".infinite-canvas"


def legacy_static_dir() -> Path:
    return coding_root() / "static"


def legacy_assets_dir() -> Path:
    return coding_root() / "assets"


def legacy_output_dir() -> Path:
    return coding_root() / "output"


def media_preview_dir() -> Path:
    return app_data_dir() / "data" / "media_previews"


def canvases_dir() -> Path:
    return app_data_dir() / "data" / "canvases"


def projects_file() -> Path:
    return app_data_dir() / "data" / "projects.json"


def legacy_canvases_dir() -> Path:
    return coding_root() / "data" / "canvases"


def legacy_projects_file() -> Path:
    return coding_root() / "data" / "projects.json"


def assets_input_dir() -> Path:
    return app_data_dir() / "assets" / "input"


def assets_output_dir() -> Path:
    return app_data_dir() / "assets" / "output"


def ensure_app_data_dirs() -> None:
    root = app_data_dir()
    for sub in ("data", "assets", "config"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "data" / "canvases").mkdir(parents=True, exist_ok=True)
    (root / "data" / "media_previews").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "input").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "output").mkdir(parents=True, exist_ok=True)
