"""Media preview, content-type, and path helpers — migrated from legacy main.py."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
from pathlib import Path

from PIL import Image, ImageOps

from infinite_canvas.core.paths import (
    assets_input_dir,
    assets_output_dir,
    legacy_assets_dir,
    legacy_output_dir,
    media_preview_dir,
)

VIDEO_PREVIEW_EXTS = {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"}


def sanitize_export_filename(name: str, fallback: str) -> str:
    base = os.path.basename(str(name or "").strip()) or fallback
    base = re.sub(r'[\\/:*?"<>|]+', "_", base)
    return base or fallback


def filename_from_media_url(url: str, fallback: str = "download.bin") -> str:
    path = urllib.parse.urlsplit(str(url or "")).path
    name = os.path.basename(urllib.parse.unquote(path))
    return sanitize_export_filename(name or fallback, fallback)


def output_path_for(filename: str, category: str = "output") -> Path:
    if category == "input":
        return assets_input_dir() / filename
    return assets_output_dir() / filename


def output_url_for(filename: str, category: str = "output") -> str:
    subdir = "input" if category == "input" else "output"
    return f"/assets/{subdir}/{filename}"


def local_media_file_by_basename(name: str) -> Path | None:
    safe = os.path.basename(urllib.parse.unquote(str(name or "")))
    if not safe:
        return None
    roots = [
        assets_output_dir(),
        assets_input_dir(),
        legacy_assets_dir() / "output",
        legacy_assets_dir() / "input",
        legacy_assets_dir() / "library",
        legacy_output_dir(),
    ]
    for root in roots:
        if not root.is_dir():
            continue
        root_resolved = root.resolve()
        path = (root / safe).resolve()
        try:
            path.relative_to(root_resolved)
        except ValueError:
            continue
        if path.is_file():
            return path
    return None


def content_type_for_path(path: str | Path) -> str:
    ext = os.path.splitext(str(path))[1].lower()
    mapping = {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".flv": "video/x-flv",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".gif": "image/gif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".txt": "text/plain; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".csv": "text/csv; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".srt": "application/x-subrip; charset=utf-8",
        ".vtt": "text/vtt; charset=utf-8",
        ".png": "image/png",
    }
    return mapping.get(ext, "application/octet-stream")


def image_has_alpha(img: Image.Image) -> bool:
    if img.mode in ("RGBA", "LA"):
        return True
    if img.mode == "P":
        return "transparency" in img.info
    return False


def media_preview_cache_paths(path: str | Path, width: int) -> tuple[Path, Path]:
    stat = os.stat(path)
    key = hashlib.sha1(
        f"{os.path.abspath(path)}|{stat.st_mtime_ns}|{stat.st_size}|{width}".encode("utf-8", "ignore")
    ).hexdigest()
    preview_dir = media_preview_dir()
    return preview_dir / f"{key}.webp", preview_dir / f"{key}.png"


def image_jpeg_cache_path(path: str | Path, width: int) -> Path:
    stat = os.stat(path)
    key = hashlib.sha1(
        f"{os.path.abspath(path)}|{stat.st_mtime_ns}|{stat.st_size}|{width}|jpg".encode(
            "utf-8", "ignore"
        )
    ).hexdigest()
    return media_preview_dir() / f"{key}.jpg"


def is_video_preview_file(path: str | Path) -> bool:
    return os.path.splitext(str(path).split("?", 1)[0])[1].lower() in VIDEO_PREVIEW_EXTS


def generate_video_preview_image(path: str | Path, width: int) -> Image.Image:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法生成视频预览图")
    fd, frame_path = tempfile.mkstemp(prefix="media_preview_frame_", suffix=".jpg")
    os.close(fd)
    try:
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            "0.5",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            f"scale='min({width},iw)':-2",
            frame_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0 or not os.path.exists(frame_path) or os.path.getsize(frame_path) <= 0:
            raise RuntimeError((proc.stderr or "ffmpeg 未能抽取视频首帧").strip()[:300])
        with Image.open(frame_path) as frame:
            img = ImageOps.exif_transpose(frame).copy()
            img.thumbnail((width, width), Image.LANCZOS)
            return img.convert("RGB")
    finally:
        try:
            os.remove(frame_path)
        except OSError:
            pass


def build_media_preview(path: str | Path, width: int) -> tuple[Path, str]:
    preview_dir = media_preview_dir()
    preview_dir.mkdir(parents=True, exist_ok=True)
    webp_path, png_path = media_preview_cache_paths(path, width)
    if is_video_preview_file(path):
        img = generate_video_preview_image(path, width)
    else:
        with Image.open(path) as source:
            img = ImageOps.exif_transpose(source)
            img.thumbnail((width, width), Image.LANCZOS)
            img = img.convert("RGBA" if image_has_alpha(img) else "RGB")
    try:
        img.save(webp_path, format="WEBP", quality=80, method=1)
        return webp_path, "image/webp"
    except Exception:
        img.save(png_path, format="PNG")
        return png_path, "image/png"


def build_image_jpeg(path: str | Path, width: int) -> Path:
    preview_dir = media_preview_dir()
    preview_dir.mkdir(parents=True, exist_ok=True)
    cache_path = image_jpeg_cache_path(path, width)
    with Image.open(path) as src:
        img = ImageOps.exif_transpose(src)
        if width:
            img.thumbnail((width, width), Image.LANCZOS)
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            rgba = img.convert("RGBA")
            bg.paste(rgba, mask=rgba.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")
        img.save(cache_path, format="JPEG", quality=86)
    return cache_path
