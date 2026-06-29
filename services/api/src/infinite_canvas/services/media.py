"""Media preview, download, view, and upload — migrated from legacy main.py."""

from __future__ import annotations

import asyncio
import os
import urllib.parse
from typing import Any

import requests
from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse

from infinite_canvas.core.comfyui import comfyui_instances
from infinite_canvas.core.media import (
    build_image_jpeg,
    build_media_preview,
    content_type_for_path,
    filename_from_media_url,
    image_jpeg_cache_path,
    local_media_file_by_basename,
    media_preview_cache_paths,
    output_path_for,
    sanitize_export_filename,
)
from infinite_canvas.core.output_files import output_file_from_url


async def media_preview(url: str, w: int = 512) -> FileResponse:
    path = output_file_from_url(url)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    width = max(64, min(2048, int(w or 512)))
    webp_path, png_path = media_preview_cache_paths(path, width)

    if webp_path.is_file():
        return FileResponse(webp_path, media_type="image/webp")
    if png_path.is_file():
        return FileResponse(png_path, media_type="image/png")

    try:
        out_path, media_type = await asyncio.to_thread(build_media_preview, path, width)
        return FileResponse(out_path, media_type=media_type)
    except Exception as exc:
        raise HTTPException(status_code=415, detail=f"无法生成预览图：{exc}") from exc


async def image_jpeg(url: str, w: int = 0) -> FileResponse:
    path = output_file_from_url(url)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="媒体文件不存在")

    width = max(0, min(4096, int(w or 0)))
    cache_path = image_jpeg_cache_path(path, width)
    if cache_path.is_file():
        return FileResponse(cache_path, media_type="image/jpeg")

    try:
        out_path = await asyncio.to_thread(build_image_jpeg, path, width)
        return FileResponse(out_path, media_type="image/jpeg")
    except Exception as exc:
        raise HTTPException(status_code=415, detail=f"无法转换图片：{exc}") from exc


def view_image(filename: str, type: str = "input", subfolder: str = "") -> Response | FileResponse:
    for addr in comfyui_instances():
        try:
            url = f"http://{addr}/view"
            params = {"filename": filename, "type": type, "subfolder": subfolder}
            r = requests.get(url, params=params, timeout=1)
            if r.status_code == 200:
                return Response(content=r.content, media_type=r.headers.get("Content-Type"))
        except Exception:
            continue

    if not subfolder and type in ("input", "output"):
        safe_name = os.path.basename(filename or "")
        if safe_name:
            local_path = output_path_for(safe_name, "input" if type == "input" else "output")
            if local_path.is_file():
                return FileResponse(local_path, media_type=content_type_for_path(local_path))
    raise HTTPException(status_code=404, detail="Image not found on any available backend")


def download_output(request: Request, url: str, name: str = "", inline: bool = False) -> FileResponse | StreamingResponse:
    path = output_file_from_url(url)
    if not path:
        local = local_media_file_by_basename(filename_from_media_url(url, ""))
        path = local
    if path and path.is_file():
        filename = sanitize_export_filename(
            os.path.basename(name) if name else os.path.basename(path),
            os.path.basename(path),
        )
        return FileResponse(
            path,
            media_type=content_type_for_path(path),
            filename=None if inline else filename,
        )

    parsed = urllib.parse.urlparse(str(url or "").strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="无效的下载地址")
    try:
        upstream_headers = {"User-Agent": "ComfyUI-API-Modelscope/1.0"}
        range_header = request.headers.get("range")
        if range_header:
            upstream_headers["Range"] = range_header
        upstream = requests.get(
            url, stream=True, timeout=(10, 60), headers=upstream_headers
        )
        upstream.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"远程文件下载失败：{exc}") from exc

    content_type = upstream.headers.get("content-type") or "application/octet-stream"
    fallback = filename_from_media_url(url, "download.bin")
    filename = sanitize_export_filename(
        os.path.basename(name) if name else fallback, fallback
    )
    disposition = "inline" if inline else "attachment"
    headers: dict[str, str] = {
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{urllib.parse.quote(filename)}"
    }
    content_length = upstream.headers.get("content-length")
    if content_length:
        headers["Content-Length"] = content_length
    for key in ("content-range", "accept-ranges"):
        value = upstream.headers.get(key)
        if value:
            headers["-".join(part.capitalize() for part in key.split("-"))] = value

    def stream_remote():
        try:
            for chunk in upstream.iter_content(chunk_size=256 * 1024):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return StreamingResponse(
        stream_remote(),
        media_type=content_type,
        headers=headers,
        status_code=upstream.status_code,
    )


async def upload_image(files: list[UploadFile]) -> dict[str, list[dict[str, Any]]]:
    uploaded_files: list[dict[str, Any]] = []
    files_content: list[tuple[UploadFile, bytes]] = []
    for file in files:
        content = await file.read()
        files_content.append((file, content))

    for file, content in files_content:
        success_count = 0
        last_result: dict[str, Any] | None = None
        for addr in comfyui_instances():
            try:
                files_data = {"image": (file.filename, content, file.content_type)}
                response = requests.post(
                    f"http://{addr}/upload/image", files=files_data, timeout=5
                )
                if response.status_code == 200:
                    last_result = response.json()
                    success_count += 1
            except Exception as exc:
                print(f"Upload error for {addr}: {exc}")

        if success_count > 0 and last_result:
            uploaded_files.append({"comfy_name": last_result.get("name", file.filename)})
        else:
            raise HTTPException(status_code=500, detail="Failed to upload to any backend")

    return {"files": uploaded_files}
