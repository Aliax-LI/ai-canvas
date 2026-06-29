"""Canvas assets, workflows, and prompt templates — Batch 7."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, File, Form, UploadFile

from infinite_canvas.schemas.canvas_assets import (
    CanvasAssetCheckRequest,
    CanvasAssetDownloadRequest,
    CanvasWorkflowExportRequest,
)
from infinite_canvas.services import canvas_assets, canvas_workflows

router = APIRouter(tags=["canvas-assets"])


@router.get("/api/canvas-assets")
async def list_canvas_assets():
    return await asyncio.to_thread(canvas_assets.canvas_assets_index)


@router.get("/api/smart-canvas/prompt-templates")
async def smart_canvas_prompt_templates():
    return canvas_assets.smart_canvas_prompt_templates()


@router.post("/api/canvas-assets/check")
async def check_canvas_assets(payload: CanvasAssetCheckRequest):
    return canvas_assets.check_canvas_assets(payload)


@router.post("/api/canvas-assets/download")
async def download_canvas_assets(payload: CanvasAssetDownloadRequest):
    return canvas_assets.download_canvas_assets(payload)


@router.post("/api/canvas-workflows/export")
async def export_canvas_workflow(payload: CanvasWorkflowExportRequest):
    return canvas_workflows.export_canvas_workflow(payload)


@router.post("/api/canvas-workflows/export-to-library")
async def export_canvas_workflow_to_library(payload: CanvasWorkflowExportRequest):
    return canvas_workflows.export_canvas_workflow_to_library(payload)


@router.post("/api/asset-library/workflows/upload")
async def upload_asset_library_workflows(
    files: list[UploadFile] = File(...),
    library_id: str = Form(""),
    category_id: str = Form(""),
):
    return await canvas_workflows.upload_asset_library_workflows(files, library_id, category_id)


@router.post("/api/canvas-workflows/import")
async def import_canvas_workflow(file: UploadFile = File(...)):
    return await canvas_workflows.import_canvas_workflow(file)
