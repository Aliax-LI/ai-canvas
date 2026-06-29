"""Local data store management — for desktop app and ops."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from infinite_canvas.core.database import (
    init_database,
    is_migration_done,
    list_setting_keys,
    store_stats,
    use_sqlite_storage,
)
from infinite_canvas.core.paths import database_file
from infinite_canvas.services.data_migration import migrate_files_to_database

router = APIRouter(tags=["data-store"])


class MigrateRequest(BaseModel):
    force: bool = False


@router.get("/api/data/store")
def data_store_info():
    init_database()
    path = database_file()
    return {
        "storage": "sqlite" if use_sqlite_storage() else "files",
        "database_path": str(path),
        "database_exists": path.is_file(),
        "database_size_bytes": path.stat().st_size if path.is_file() else 0,
        "files_migrated": is_migration_done(),
        "stats": store_stats() if use_sqlite_storage() else {},
        "setting_keys": list_setting_keys() if use_sqlite_storage() else [],
    }


@router.post("/api/data/migrate-from-files")
def migrate_from_files(payload: MigrateRequest):
    if not use_sqlite_storage():
        raise HTTPException(
            status_code=400,
            detail="当前为 files 存储模式，请设置 INFINITE_CANVAS_STORAGE=sqlite 后重试",
        )
    init_database()
    if is_migration_done() and not payload.force:
        return {"ok": True, "skipped": True, "message": "已完成文件迁移；如需强制重新导入请传 force=true"}
    stats = migrate_files_to_database(force=payload.force)
    return {"ok": True, "imported": stats, "stats": store_stats()}
