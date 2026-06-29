"""Cloud upload endpoints — legacy parity."""

from __future__ import annotations

from fastapi import APIRouter, Request

from infinite_canvas.core.security import ensure_same_origin_request
from infinite_canvas.schemas.upload import CloudVideoUploadRequest, TempShUploadRequest
from infinite_canvas.services import cloud_upload

router = APIRouter(tags=["upload"])


@router.post("/api/temp-sh/upload")
async def temp_sh_upload(payload: TempShUploadRequest, request: Request):
    ensure_same_origin_request(request)
    return await cloud_upload.upload_local_video_to_cloud(payload.url, "auto")


@router.post("/api/cloud-video/upload")
async def cloud_video_upload(payload: CloudVideoUploadRequest, request: Request):
    ensure_same_origin_request(request)
    return await cloud_upload.upload_local_video_to_cloud(payload.url, payload.service)
