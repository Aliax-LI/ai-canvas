"""AI reference uploads to assets/input — legacy parity."""

from __future__ import annotations

import base64
import mimetypes
import os
import re
import shutil
import urllib.parse
import uuid
from typing import Any

from fastapi import HTTPException, UploadFile
from PIL import Image

from infinite_canvas.core.media import output_path_for, output_url_for
from infinite_canvas.schemas.ai_upload import Base64UploadRequest, LocalImageImportRequest
from infinite_canvas.services.local_assets import _local_upload_kind_ext

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v", ".flv"}
_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
_DOC_EXTS = {
    ".pdf",
    ".txt",
    ".md",
    ".markdown",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".csv",
    ".json",
    ".zip",
    ".yaml",
    ".yml",
    ".log",
}
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_LOCAL_IMAGE_IMPORT_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_LOCAL_IMAGE_IMPORT_MAX_BYTES = int(os.getenv("LOCAL_IMAGE_IMPORT_MAX_BYTES", str(50 * 1024 * 1024)))


def normalize_local_image_path(value: str) -> str:
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        raise HTTPException(status_code=400, detail="本地图片路径为空")
    if text.lower().startswith("file:"):
        parsed = urllib.parse.urlparse(text)
        if parsed.scheme.lower() != "file":
            raise HTTPException(status_code=400, detail="只支持本地图片路径")
        if parsed.netloc and re.match(r"^[a-zA-Z]:$", parsed.netloc) and os.name == "nt":
            path = f"{parsed.netloc}{urllib.parse.url2pathname(parsed.path or '')}"
        elif parsed.netloc and parsed.netloc.lower() not in ("localhost",):
            raise HTTPException(status_code=400, detail="只支持本机图片路径")
        else:
            path = urllib.parse.url2pathname(parsed.path or "")
    else:
        path = text
    path = path.strip().strip('"').strip("'")
    if re.match(r"^/[a-zA-Z]:[\\/]", path):
        path = path[1:]
    if re.match(r"^[a-zA-Z]:[\\/]", path):
        return os.path.abspath(path)
    if path.startswith("/") and os.name != "nt":
        return os.path.abspath(path)
    raise HTTPException(status_code=400, detail="只支持本机绝对图片路径")


def import_local_image_file(path: str) -> dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    if ext not in _LOCAL_IMAGE_IMPORT_EXTS:
        raise HTTPException(status_code=400, detail="仅支持 PNG、JPG、JPEG、WEBP、GIF 图片")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="本地图片不存在或无法读取")
    try:
        size = os.path.getsize(path)
    except OSError:
        raise HTTPException(status_code=404, detail="本地图片不存在或无法读取")
    if size <= 0:
        raise HTTPException(status_code=400, detail="本地图片为空")
    if size > _LOCAL_IMAGE_IMPORT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="本地图片过大，请使用 50MB 以内的图片")
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="文件不是可识别的图片")
    filename = f"ai_ref_{uuid.uuid4().hex[:12]}{ext}"
    dest = output_path_for(filename, "input")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(path, dest)
    except OSError:
        raise HTTPException(status_code=500, detail="导入本地图片失败") from None
    return {
        "url": output_url_for(filename, "input"),
        "name": os.path.basename(path) or filename,
        "kind": "image",
    }


async def upload_ai_reference(files: list[UploadFile]) -> dict[str, list[dict[str, Any]]]:
    uploaded: list[dict[str, Any]] = []
    for file in files:
        content = await file.read()
        if not content:
            continue
        if len(content) > _MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"{file.filename or '文件'} 超过 50MB，无法上传")
        ext = os.path.splitext(file.filename or "")[1].lower()
        content_type = (file.content_type or "").lower()
        kind = "image"
        if ext in _VIDEO_EXTS or content_type.startswith("video/"):
            kind = "video"
            if ext not in _VIDEO_EXTS:
                ext = ".webm" if "webm" in content_type else ".mov" if "quicktime" in content_type else ".mp4"
        elif ext in _AUDIO_EXTS or content_type.startswith("audio/"):
            kind = "audio"
            if ext not in _AUDIO_EXTS:
                ext = ".wav" if "wav" in content_type else ".ogg" if "ogg" in content_type else ".m4a" if "mp4" in content_type else ".mp3"
        elif ext in _IMAGE_EXTS or content_type.startswith("image/"):
            kind = "image"
            if ext not in _IMAGE_EXTS:
                ext = ".jpg" if "jpeg" in content_type else ".webp" if "webp" in content_type else ".gif" if "gif" in content_type else ".png"
        elif ext in _DOC_EXTS or content_type.startswith(("text/", "application/")):
            kind = "file"
            if not ext:
                ext = mimetypes.guess_extension(content_type) or ".bin"
        else:
            kind = "file"
            if not ext:
                ext = ".bin"
        filename = f"ai_ref_{uuid.uuid4().hex[:12]}{ext}"
        path = output_path_for(filename, "input")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        uploaded.append(
            {
                "url": output_url_for(filename, "input"),
                "name": file.filename or filename,
                "kind": kind,
                "mime": content_type,
            }
        )
    return {"files": uploaded}


async def upload_ai_base64(payload: Base64UploadRequest) -> dict[str, list[dict[str, Any]]]:
    raw = (payload.data or "").strip()
    ct = (payload.content_type or "").split(";", 1)[0].strip().lower()
    if raw.startswith("data:"):
        header, _, raw = raw.partition(",")
        if not ct:
            ct = header[5:].split(";", 1)[0].strip().lower()
    try:
        content = base64.b64decode(raw, validate=False)
    except Exception:
        raise HTTPException(status_code=400, detail="数据无法解码") from None
    if not content:
        raise HTTPException(status_code=400, detail="内容为空")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="超过 50MB")
    kind, ext = _local_upload_kind_ext(payload.name or "", ct or "image/png")
    if kind is None:
        kind, ext = "image", ".png"
    filename = f"ai_ref_{uuid.uuid4().hex[:12]}{ext}"
    path = output_path_for(filename, "input")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return {
        "files": [
            {
                "url": output_url_for(filename, "input"),
                "name": payload.name or filename,
                "kind": kind,
            }
        ]
    }


def import_local_ai_reference(payload: LocalImageImportRequest) -> dict[str, list[dict[str, Any]]]:
    requested = [payload.path] if payload.path else []
    requested.extend(payload.paths or [])
    requested = [p for p in requested if str(p or "").strip()][:20]
    if not requested:
        raise HTTPException(status_code=400, detail="没有可导入的本地图片")
    return {
        "files": [import_local_image_file(normalize_local_image_path(path)) for path in requested]
    }
