"""Media reference URL helpers for chat and canvas LLM — legacy parity subset."""

from __future__ import annotations

import asyncio
import base64
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
from io import BytesIO
from typing import Any

import httpx
from PIL import Image

from infinite_canvas.core.media import content_type_for_path
from infinite_canvas.core.output_files import output_file_from_url


def is_image_reference_value(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith("data:image/"):
        return True
    if text.startswith(("http://", "https://", "/output/", "/assets/")):
        clean = text.split("?", 1)[0].split("#", 1)[0].lower()
        return bool(re.search(r"\.(png|jpe?g|webp|gif|bmp|tiff?)$", clean)) or text.startswith("/")
    return False


def is_video_reference_value(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith(("http://", "https://", "/output/", "/assets/")):
        clean = text.split("?", 1)[0].split("#", 1)[0].lower()
        return bool(re.search(r"\.(mp4|webm|mov|m4v|avi|mkv|flv)(\?|$)", clean))
    return False


def reference_to_data_url(ref: dict[str, Any] | str, max_size: int | None = 1536) -> str:
    if isinstance(ref, str):
        ref = {"url": ref}
    value = str((ref or {}).get("url") or "").strip()
    if not value:
        return ""
    if value.startswith("data:"):
        return value
    if value.startswith(("http://", "https://")):
        return value
    path = output_file_from_url(value)
    if not path or not path.is_file():
        return ""
    try:
        with Image.open(path) as img:
            img.load()
            if max_size and max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.LANCZOS)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            buf = BytesIO()
            fmt = "PNG" if img.mode == "RGBA" else "JPEG"
            img.save(buf, format=fmt, quality=88 if fmt == "JPEG" else None)
            encoded = base64.b64encode(buf.getvalue()).decode("ascii")
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            return f"data:{mime};base64,{encoded}"
    except Exception as exc:
        print(f"reference_to_data_url failed: {exc}")
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{content_type_for_path(path)};base64,{encoded}"


def media_reference_to_url(value: str, max_image_size: int | None = 1024) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith(("http://", "https://", "data:")):
        return text
    if text.startswith(("/output/", "/assets/")):
        return reference_to_data_url({"url": text}, max_size=max_image_size)
    return ""


async def video_reference_to_frame_data_urls(value: str, max_frames: int = 6, max_size: int = 768) -> list[str]:
    if not isinstance(value, str) or not value:
        return []
    path_obj = output_file_from_url(value)
    path = str(path_obj) if path_obj else ""
    cleanup_path = ""
    if not path and value.startswith(("http://", "https://")):
        suffix = os.path.splitext(urllib.parse.urlparse(value).path)[1] or ".mp4"
        fd, cleanup_path = tempfile.mkstemp(prefix="canvas_llm_video_", suffix=suffix)
        os.close(fd)
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=20.0, read=120.0, write=30.0, pool=10.0)
            ) as client:
                response = await client.get(value)
                response.raise_for_status()
                with open(cleanup_path, "wb") as f:
                    f.write(response.content)
            path = cleanup_path
        except Exception as exc:
            print(f"[canvas-llm] video download failed: {exc}")
            if cleanup_path and os.path.exists(cleanup_path):
                try:
                    os.remove(cleanup_path)
                except OSError:
                    pass
            return []
    if not path or not os.path.exists(path):
        return []
    frame_dir = tempfile.mkdtemp(prefix="canvas_llm_frames_")
    try:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return []
        pattern = os.path.join(frame_dir, "frame_%03d.jpg")
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            path,
            "-vf",
            f"fps=1,scale='min({max_size},iw)':-2",
            "-frames:v",
            str(max(1, max_frames)),
            pattern,
        ]
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode != 0:
            print(f"[canvas-llm] ffmpeg frame extract failed: {(proc.stderr or '')[:300]}")
            return []
        frames: list[str] = []
        for name in sorted(os.listdir(frame_dir)):
            if not name.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            frame_path = os.path.join(frame_dir, name)
            frames.append(reference_to_data_url({"url": frame_path}, max_size=max_size))
            if len(frames) >= max_frames:
                break
        return [item for item in frames if item]
    finally:
        if cleanup_path and os.path.exists(cleanup_path):
            try:
                os.remove(cleanup_path)
            except OSError:
                pass
        shutil.rmtree(frame_dir, ignore_errors=True)
