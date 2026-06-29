"""Shared folders HTTP routes — Batch 4b."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.schemas.asset_libraries import SharedFolderImport, SharedFolderRegister
from infinite_canvas.services import asset_ai, asset_library_store, shared_folders_store

router = APIRouter(tags=["shared-folders"])


@router.get("/api/shared-folders")
async def list_shared_folders():
    return {"folders": shared_folders_store.list_shared_folders_public()}


@router.post("/api/shared-folders")
async def register_shared_folder(payload: SharedFolderRegister):
    folder = shared_folders_store.register_shared_folder(payload.path, payload.name)
    return {"folder": folder}


@router.delete("/api/shared-folders/{folder_id}")
async def unregister_shared_folder(folder_id: str):
    shared_folders_store.unregister_shared_folder(folder_id)
    return {"ok": True}


@router.get("/api/shared-folders/{folder_id}/tree")
async def get_shared_folder_tree(folder_id: str):
    entry = shared_folders_store.shared_folder_by_id(folder_id)
    if not entry:
        raise HTTPException(status_code=404, detail="共享文件夹不存在")
    abs_path = shared_folders_store.shared_folder_abs(entry)
    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="文件夹已不存在")
    tree = shared_folders_store.scan_shared_tree(
        folder_id, abs_path, "", entry.get("name") or os.path.basename(abs_path)
    )
    return {
        "folder": {"id": folder_id, "name": entry.get("name"), "path": abs_path},
        "tree": tree,
    }


@router.get("/api/shared-folders/{folder_id}/file")
async def get_shared_folder_file(folder_id: str, path: str = ""):
    entry = shared_folders_store.shared_folder_by_id(folder_id)
    if not entry:
        raise HTTPException(status_code=404, detail="共享文件夹不存在")
    folder_abs = shared_folders_store.shared_folder_abs(entry)
    abs_path = shared_folders_store.shared_child_abs(folder_abs, path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    ext = os.path.splitext(abs_path)[1].lower()
    if ext not in shared_folders_store.SHARED_MEDIA_EXTS:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    return FileResponse(abs_path, media_type=shared_folders_store.shared_folder_media_type(abs_path))


@router.post("/api/shared-folders/import")
async def import_shared_folder_files(payload: SharedFolderImport):
    entry = shared_folders_store.shared_folder_by_id(payload.folder_id)
    if not entry:
        raise HTTPException(status_code=404, detail="共享文件夹不存在")
    folder_abs = shared_folders_store.shared_folder_abs(entry)
    lib = asset_library_store.load_asset_library()
    cat = asset_library_store.find_asset_category_in_library(lib, payload.category_id, payload.library_id)
    if not cat:
        raise HTTPException(status_code=404, detail="分类不存在")
    if cat.get("type") != "image":
        raise HTTPException(status_code=400, detail="该分类暂不支持添加媒体")
    added = []
    for rel in (payload.paths or [])[:200]:
        abs_path = shared_folders_store.shared_child_abs(folder_abs, rel)
        if not os.path.isfile(abs_path):
            continue
        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in shared_folders_store.SHARED_MEDIA_EXTS:
            continue
        _, item = asset_library_store.make_asset_library_item(
            abs_path, os.path.basename(abs_path), subdir=cat.get("dir") or ""
        )
        if item.get("kind") == "image":
            classification = await asset_ai.classify_asset_image_best_effort(
                str(output_file_from_url(item.get("url") or "") or abs_path)
            )
            if classification:
                item["classification"] = classification
        cat.setdefault("items", []).append(item)
        added.append(item)
    asset_library_store.save_asset_library(lib)
    return {"library": lib, "items": added}
