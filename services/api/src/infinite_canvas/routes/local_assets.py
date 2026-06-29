"""Local asset manager HTTP routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, File, Form, Request, UploadFile

from infinite_canvas.core.security import ensure_same_origin_request
from infinite_canvas.schemas.local_assets import (
    LocalAssetCaptionRequest,
    LocalAssetCaptionSaveRequest,
    LocalAssetClassifyRequest,
    LocalAssetDeleteRequest,
    LocalAssetFolderRequest,
    LocalAssetMoveRequest,
    LocalAssetRenameRequest,
    LocalAssetUrlImportRequest,
)
from infinite_canvas.services import local_assets as local_assets_service

router = APIRouter(tags=["local-assets"])


@router.post("/api/local-assets/upload")
async def upload_local_assets(files: List[UploadFile] = File(...), folder: str = Form("")):
    return await local_assets_service.upload_local_assets(files, folder)


@router.post("/api/local-assets/import-urls")
async def import_local_assets_from_urls(payload: LocalAssetUrlImportRequest):
    return await local_assets_service.import_local_assets_from_urls(payload)


@router.get("/api/local-assets")
async def list_local_assets():
    return local_assets_service.list_local_assets()


@router.post("/api/local-assets/folders")
async def create_local_asset_folder(payload: LocalAssetFolderRequest, request: Request):
    ensure_same_origin_request(request)
    return local_assets_service.create_local_asset_folder(payload)


@router.patch("/api/local-assets/folders")
async def rename_local_asset_folder(payload: LocalAssetFolderRequest, request: Request):
    ensure_same_origin_request(request)
    return local_assets_service.rename_local_asset_folder(payload)


@router.patch("/api/local-assets/items")
async def rename_local_asset_item(payload: LocalAssetRenameRequest, request: Request):
    ensure_same_origin_request(request)
    return local_assets_service.rename_local_asset_item(payload)


@router.post("/api/local-assets/delete")
async def delete_local_assets(payload: LocalAssetDeleteRequest, request: Request):
    ensure_same_origin_request(request)
    return local_assets_service.delete_local_assets(payload.names)


@router.post("/api/local-assets/move")
async def move_local_assets(payload: LocalAssetMoveRequest, request: Request):
    ensure_same_origin_request(request)
    return local_assets_service.move_local_assets(payload.names, payload.folder)


@router.post("/api/local-assets/caption")
async def caption_local_assets(payload: LocalAssetCaptionRequest):
    return await local_assets_service.caption_local_assets(payload)


@router.post("/api/local-assets/classify")
async def classify_local_assets(payload: LocalAssetClassifyRequest):
    return await local_assets_service.classify_local_assets(payload)


@router.patch("/api/local-assets/caption")
async def save_local_asset_caption(payload: LocalAssetCaptionSaveRequest):
    return local_assets_service.save_local_asset_caption(payload)
