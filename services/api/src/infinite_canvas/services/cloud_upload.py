"""Temp.sh / Litterbox cloud video upload — legacy parity."""

from __future__ import annotations

import os
import re

import httpx
from fastapi import HTTPException

from infinite_canvas.core.media import content_type_for_path
from infinite_canvas.core.output_files import output_file_from_url


def local_media_path_for_cloud_upload(ref_url: str, allowed_prefixes: tuple[str, ...] = ("image/", "video/")) -> str:
    ref_url = str(ref_url or "").strip()
    if not ref_url:
        raise HTTPException(status_code=400, detail="没有可上传的媒体文件")
    if ref_url.startswith("http://") or ref_url.startswith("https://"):
        return ""
    if not (ref_url.startswith("/output/") or ref_url.startswith("/assets/")):
        raise HTTPException(status_code=400, detail="云端上传只支持画布里的本地图片或视频文件")
    path_obj = output_file_from_url(ref_url)
    if not path_obj or not path_obj.is_file():
        raise HTTPException(status_code=404, detail="本地媒体文件不存在或已被删除")
    path = str(path_obj)
    ct = content_type_for_path(path)
    if not any(ct.startswith(prefix) for prefix in allowed_prefixes):
        raise HTTPException(status_code=400, detail="请选择图片或视频文件再上传云端")
    max_bytes = int(os.getenv("TEMP_SH_MAX_BYTES", str(4 * 1024 * 1024 * 1024)))
    size = os.path.getsize(path)
    if size > max_bytes:
        raise HTTPException(status_code=400, detail=f"媒体文件超过云端上传大小限制：{size} bytes")
    return path


async def upload_video_to_litterbox(path: str, source_url: str) -> dict[str, str]:
    upload_url = (
        os.getenv("LITTERBOX_UPLOAD_URL", "https://litterbox.catbox.moe/resources/internals/api.php").strip()
        or "https://litterbox.catbox.moe/resources/internals/api.php"
    )
    time_value = os.getenv("LITTERBOX_TIME", "72h").strip() or "72h"
    ct = content_type_for_path(path)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=20.0, read=600.0, write=600.0, pool=20.0),
            follow_redirects=True,
        ) as client:
            with open(path, "rb") as fh:
                files = {"fileToUpload": (os.path.basename(path), fh, ct)}
                data = {"reqtype": "fileupload", "time": time_value}
                response = await client.post(upload_url, data=data, files=files)
        if not response.is_success:
            raise HTTPException(status_code=response.status_code, detail=f"Litterbox 上传失败：{response.text[:300]}")
        direct_url = response.text.strip().splitlines()[0].strip()
        if not re.match(r"^https?://", direct_url, re.I):
            raise HTTPException(status_code=502, detail=f"Litterbox 返回了无法识别的链接：{response.text[:300]}")
        return {
            "url": direct_url,
            "source": source_url,
            "name": os.path.basename(path),
            "expires": time_value,
            "service": "litterbox",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Litterbox 上传异常：{exc}") from exc


async def upload_video_to_temp_sh(path: str, source_url: str) -> dict[str, str]:
    upload_url = os.getenv("TEMP_SH_UPLOAD_URL", "https://temp.sh/upload").strip() or "https://temp.sh/upload"
    ct = content_type_for_path(path)
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=20.0, read=600.0, write=600.0, pool=20.0),
            follow_redirects=True,
        ) as client:
            with open(path, "rb") as fh:
                files = {"file": (os.path.basename(path), fh, ct)}
                response = await client.post(upload_url, files=files)
        if not response.is_success:
            raise HTTPException(status_code=response.status_code, detail=f"Temp.sh 上传失败：{response.text[:300]}")
        direct_url = response.text.strip().splitlines()[0].strip()
        if not re.match(r"^https?://", direct_url, re.I):
            raise HTTPException(status_code=502, detail=f"Temp.sh 返回了无法识别的链接：{response.text[:300]}")
        return {
            "url": direct_url,
            "source": source_url,
            "name": os.path.basename(path),
            "expires": "3 days",
            "service": "temp.sh",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Temp.sh 上传异常：{exc}") from exc


async def upload_local_video_to_cloud(ref_url: str, service: str = "auto") -> dict[str, str]:
    ref_url = str(ref_url or "").strip()
    if ref_url.startswith("http://") or ref_url.startswith("https://"):
        return {"url": ref_url, "source": ref_url, "service": "existing"}
    path = local_media_path_for_cloud_upload(ref_url)
    service = str(service or os.getenv("CLOUD_VIDEO_UPLOAD_SERVICE", "auto") or "auto").strip().lower()
    if service in {"litterbox", "catbox"}:
        return await upload_video_to_litterbox(path, ref_url)
    if service in {"temp", "temp.sh", "tempsh"}:
        return await upload_video_to_temp_sh(path, ref_url)
    errors: list[str] = []
    for name, func in (("litterbox", upload_video_to_litterbox), ("temp.sh", upload_video_to_temp_sh)):
        try:
            return await func(path, ref_url)
        except HTTPException as exc:
            errors.append(f"{name}: {exc.detail}")
    raise HTTPException(status_code=502, detail="云端上传失败：" + "；".join(errors))
