"""Media preview, download, view, and upload endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, File, Request, UploadFile

from infinite_canvas.services import media as media_service

router = APIRouter(tags=["media"])


@router.get("/api/media-preview")
async def media_preview(url: str, w: int = 512):
    return await media_service.media_preview(url, w)


@router.get("/api/image-jpeg")
async def image_jpeg(url: str, w: int = 0):
    return await media_service.image_jpeg(url, w)


@router.get("/api/view")
def view_image(filename: str, type: str = "input", subfolder: str = ""):
    return media_service.view_image(filename, type, subfolder)


@router.get("/api/download-output")
def download_output(request: Request, url: str, name: str = "", inline: bool = False):
    return media_service.download_output(request, url, name, inline)


@router.post("/api/upload")
async def upload_image(files: List[UploadFile] = File(...)):
    return await media_service.upload_image(files)
