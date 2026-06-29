"""AI reference upload routes — Batch 7."""

from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile

from infinite_canvas.core.security import ensure_same_origin_request
from infinite_canvas.schemas.ai_upload import Base64UploadRequest, LocalImageImportRequest
from infinite_canvas.services import ai_upload

router = APIRouter(tags=["ai-upload"])


@router.post("/api/ai/upload")
async def upload_ai_reference(files: list[UploadFile] = File(...)):
    return await ai_upload.upload_ai_reference(files)


@router.post("/api/ai/upload-base64")
async def upload_ai_base64(payload: Base64UploadRequest):
    return await ai_upload.upload_ai_base64(payload)


@router.post("/api/ai/import-local-image")
async def import_local_ai_reference(payload: LocalImageImportRequest, request: Request):
    ensure_same_origin_request(request)
    return ai_upload.import_local_ai_reference(payload)
