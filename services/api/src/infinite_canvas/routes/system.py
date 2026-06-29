"""System and health endpoints (Phase 0)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from infinite_canvas import __version__
from infinite_canvas.core.config import get_settings
from infinite_canvas.core.database import use_sqlite_storage
from infinite_canvas.core.paths import (
    coding_root,
    database_file,
    legacy_static_dir,
    repo_root,
)

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@router.get("/api/app-info")
def app_info():
    settings = get_settings()
    static = legacy_static_dir()
    coding = coding_root()
    return {
        "name": "infinite-canvas",
        "version": __version__,
        "phase": "1-backend",
        "storage": "sqlite" if use_sqlite_storage() else "files",
        "database_path": str(database_file()),
        "repo_root": str(repo_root()),
        "coding_root": str(coding),
        "coding_present": coding.is_dir(),
        "legacy_static_present": static.is_dir(),
        "data_dir": settings.data_dir,
        "host": settings.host,
        "port": settings.port,
    }
