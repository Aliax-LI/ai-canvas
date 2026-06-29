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


def local_upload_dir() -> Path:
    """Local asset manager uploads (legacy LOCAL_UPLOAD_DIR)."""
    return app_data_dir() / "assets" / "uploads"


def asset_library_dir() -> Path:
    return app_data_dir() / "assets" / "library"


def asset_library_file() -> Path:
    return app_data_dir() / "data" / "asset_library.json"


def prompt_libraries_file() -> Path:
    return app_data_dir() / "data" / "prompt_libraries.json"


def app_assets_dir() -> Path:
    """User-writable assets root served at /assets."""
    return app_data_dir() / "assets"


def api_env_file() -> Path:
    return app_data_dir() / "config" / ".env"


def api_providers_file() -> Path:
    return app_data_dir() / "data" / "api_providers.json"


def conversations_dir() -> Path:
    return app_data_dir() / "data" / "conversations"


def global_config_file() -> Path:
    """Legacy global_config.json beside upstream main.py (read-only fallback)."""
    return coding_root() / "global_config.json"


def database_file() -> Path:
    """Primary SQLite database for canvases, settings, and related app data."""
    return app_data_dir() / "infinite-canvas.db"


def static_runninghub_dir() -> Path:
    return legacy_static_dir() / "runninghub"


def ensure_app_data_dirs() -> None:
    root = app_data_dir()
    for sub in ("data", "assets", "config"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "data" / "canvases").mkdir(parents=True, exist_ok=True)
    (root / "data" / "conversations").mkdir(parents=True, exist_ok=True)
    (root / "data" / "media_previews").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "input").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "output").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "uploads").mkdir(parents=True, exist_ok=True)
    (root / "assets" / "library").mkdir(parents=True, exist_ok=True)
    (root / "config").mkdir(parents=True, exist_ok=True)
    api_env_file().touch(exist_ok=True)
