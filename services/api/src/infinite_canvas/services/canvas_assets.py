"""Canvas asset index, check, download, and prompt templates — legacy parity."""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator

import requests
from fastapi import HTTPException
from fastapi.responses import Response

from infinite_canvas.core.asset_utils import sanitize_asset_name
from infinite_canvas.core.database import list_canvas_rows, use_sqlite_storage
from infinite_canvas.core.media import filename_from_media_url, local_media_file_by_basename, sanitize_export_filename
from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.paths import legacy_static_dir, repo_root
from infinite_canvas.schemas.canvas_assets import CanvasAssetCheckRequest, CanvasAssetDownloadRequest
from infinite_canvas.services import asset_library_store, canvas_store

PROMPT_TEMPLATE_EN: dict[str, dict[str, str]] = {
    "360全景图": {
        "name": "360 Panorama VR Image",
        "scene": "Generate a seamless 360-degree VR panorama with continuous left and right edges and natural pole transitions.",
    },
}


def prompt_template_markdown_path() -> str:
    candidates = [
        legacy_static_dir() / "system-prompts" / "infinite-canvas-prompt-templates.md",
        repo_root() / "static" / "system-prompts" / "infinite-canvas-prompt-templates.md",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return ""


def prompt_template_category(name: str, scene: str) -> str:
    text = f"{name} {scene}"
    if any(k in text for k in ["光影", "灯光", "光效", "电影级"]):
        return "lighting"
    if any(k in text for k in ["视角", "全景", "VR", "镜头", "俯拍", "仰拍", "景别", "构图", "透视"]):
        return "view"
    if any(k in text for k in ["角色", "脸部", "表情", "Actor", "服装"]):
        return "character"
    if any(k in name for k in ["产品", "电商", "工业"]):
        return "product"
    return "storyboard"


def extract_prompt_template_section(block: str, title: str) -> str:
    pattern = rf"###\s*{re.escape(title)}\s*\n(?P<body>.*?)(?=\n###\s+|\Z)"
    match = re.search(pattern, block, re.S)
    if not match:
        return ""
    body = match.group("body").strip()
    fence = re.search(r"```(?:\w+)?\s*\n(?P<code>.*?)\n```", body, re.S)
    return (fence.group("code") if fence else body).strip()


def parse_prompt_template_markdown(text: str) -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    matches = list(re.finditer(r"^##\s*预设\s*(\d+)\s*[：:]\s*(.+?)\s*$", text, re.M))
    for index, match in enumerate(matches):
        number = match.group(1).strip()
        name = match.group(2).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end]
        scene = extract_prompt_template_section(block, "适用场景")
        positive = extract_prompt_template_section(block, "正向提示词")
        negative = extract_prompt_template_section(block, "负向提示词")
        params_raw = extract_prompt_template_section(block, "平台参数建议")
        params: dict[str, str] = {}
        for line in params_raw.splitlines():
            item = re.match(r"[-*]\s*\*\*(.+?)\*\*\s*[：:]\s*(.+)", line.strip())
            if item:
                params[item.group(1).strip()] = item.group(2).strip()
        if not positive:
            continue
        templates.append(
            {
                "id": f"builtin_md_{number}",
                "number": number,
                "name": name,
                "name_en": PROMPT_TEMPLATE_EN.get(name, {}).get("name", name),
                "category": prompt_template_category(name, scene),
                "scene": scene,
                "scene_en": PROMPT_TEMPLATE_EN.get(name, {}).get("scene", scene),
                "positive": positive,
                "negative": negative,
                "params": params,
                "builtin": True,
            }
        )
    return templates


def builtin_prompt_templates() -> list[dict[str, Any]]:
    try:
        template_path = prompt_template_markdown_path()
        if not template_path:
            return []
        with open(template_path, encoding="utf-8") as f:
            return parse_prompt_template_markdown(f.read())
    except Exception as exc:
        print(f"读取提示词模板失败: {exc}")
        return []


def smart_canvas_prompt_templates() -> dict[str, Any]:
    try:
        template_path = prompt_template_markdown_path()
        source = ""
        if template_path:
            try:
                source = os.path.relpath(template_path, str(repo_root())).replace("\\", "/")
            except ValueError:
                source = template_path
        return {"templates": builtin_prompt_templates(), "source": source}
    except Exception as exc:
        print(f"读取提示词模板失败: {exc}")
        return {"templates": []}


def _iter_canvas_documents(include_deleted: bool = False) -> Iterator[dict[str, Any]]:
    canvas_store.cleanup_expired_canvas_trash()
    if use_sqlite_storage():
        for doc in list_canvas_rows(include_deleted=include_deleted):
            yield doc
        return
    directory = canvas_store.canvases_dir_for_read()
    if not directory.is_dir():
        return
    for filepath in directory.iterdir():
        if filepath.suffix != ".json":
            continue
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        is_deleted = bool(data.get("deleted_at"))
        if include_deleted != is_deleted:
            continue
        yield data


def canvas_asset_url_value(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("url", "path", "src", "uri", "output", "output_url", "outputUrl", "video", "video_url", "videoUrl"):
            text = str(value.get(key) or "").strip()
            if text:
                return text
    return ""


def canvas_asset_downloadable_url(url: str) -> str:
    text = str(url or "").strip()
    return text if text.startswith(("/output/", "/assets/", "http://", "https://")) else ""


def canvas_asset_kind(value: object, url: str = "") -> str:
    explicit = ""
    if isinstance(value, dict):
        explicit = str(value.get("kind") or value.get("mediaKind") or value.get("type") or "").lower()
    if "video" in explicit:
        return "video"
    if "audio" in explicit:
        return "audio"
    if "text" in explicit:
        return "text"
    if "workflow" in explicit:
        return "workflow"
    return asset_library_store.asset_library_media_kind(url or canvas_asset_url_value(value))


def canvas_asset_name(value: object, url: str = "", fallback: str = "asset") -> str:
    if isinstance(value, dict):
        for key in ("name", "filename", "file", "title"):
            name = str(value.get(key) or "").strip()
            if name:
                return sanitize_asset_name(name, fallback)
    return sanitize_asset_name(filename_from_media_url(url, fallback), fallback)


def iter_canvas_asset_values(value: object, path: str = "") -> Iterator[tuple[str, object, str]]:
    if isinstance(value, dict):
        url = canvas_asset_downloadable_url(canvas_asset_url_value(value))
        if url:
            yield path, value, url
        for key, child in value.items():
            if key in {"run", "runs", "settings", "params", "metadata", "meta", "prompt", "text", "caption", "logs"}:
                continue
            yield from iter_canvas_asset_values(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_canvas_asset_values(child, f"{path}[{index}]")
    elif isinstance(value, str):
        url = canvas_asset_downloadable_url(value)
        if url:
            yield path, value, url


def canvas_node_title(node: dict[str, Any]) -> str:
    return str(node.get("title") or node.get("name") or node.get("label") or node.get("type") or "节点")[:120]


def extract_canvas_assets(canvas: dict[str, Any]) -> list[dict[str, Any]]:
    record = canvas_store.canvas_record(canvas)
    canvas_id = str(record.get("id") or "")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    nodes = canvas.get("nodes") if isinstance(canvas.get("nodes"), list) else []
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id") or f"node_{node_index}")
        node_title = canvas_node_title(node)
        for field_path, raw, url in iter_canvas_asset_values(node):
            if url in seen:
                continue
            seen.add(url)
            kind = canvas_asset_kind(raw, url)
            if kind not in {"image", "video", "audio", "text"}:
                continue
            fallback = f"{record.get('title') or 'canvas'}-{len(items) + 1}"
            item: dict[str, Any] = {
                "id": hashlib.sha1(f"{canvas_id}:{url}".encode("utf-8")).hexdigest()[:24],
                "url": url,
                "name": canvas_asset_name(raw, url, fallback),
                "kind": kind,
                "canvas_id": canvas_id,
                "canvas_title": record.get("title") or "未命名画布",
                "canvas_kind": record.get("kind") or "classic",
                "canvas_icon": record.get("icon") or "layers",
                "canvas_owner": record.get("owner") or "",
                "canvas_color": record.get("color") or "",
                "canvas_created_at": record.get("created_at") or 0,
                "canvas_updated_at": record.get("updated_at") or 0,
                "node_id": node_id,
                "node_title": node_title,
                "node_type": str(node.get("type") or ""),
                "source_path": field_path,
                "created_at": node.get("created_at") or record.get("updated_at") or record.get("created_at") or 0,
            }
            if isinstance(raw, dict):
                for key in ("natural_w", "natural_h", "width", "height", "size", "duration", "runMs"):
                    if raw.get(key) is not None:
                        item[key] = raw.get(key)
            items.append(item)
    return items


def canvas_assets_index() -> dict[str, Any]:
    canvases: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    canvas_counts = {"all": 0, "smart": 0, "classic": 0}
    item_counts = {"all": 0, "smart": 0, "classic": 0}
    for canvas in _iter_canvas_documents(include_deleted=False):
        record = canvas_store.canvas_record(canvas)
        canvas_items = extract_canvas_assets(canvas)
        record["asset_count"] = len(canvas_items)
        canvases.append(record)
        items.extend(canvas_items)
        kind = record.get("kind") or "classic"
        canvas_counts["all"] += 1
        canvas_counts[kind] = canvas_counts.get(kind, 0) + 1
        item_counts["all"] += len(canvas_items)
        item_counts[kind] = item_counts.get(kind, 0) + len(canvas_items)
    canvases.sort(
        key=lambda item: (0 if item.get("pinned") else 1, -int(item.get("updated_at") or item.get("created_at") or 0))
    )
    items.sort(key=lambda item: int(item.get("canvas_updated_at") or item.get("created_at") or 0), reverse=True)
    categories = [
        {"id": "all", "name": "全部画布", "count": item_counts.get("all", 0), "canvas_count": canvas_counts.get("all", 0)},
        {"id": "smart", "name": "智能画布", "count": item_counts.get("smart", 0), "canvas_count": canvas_counts.get("smart", 0)},
        {"id": "classic", "name": "普通画布", "count": item_counts.get("classic", 0), "canvas_count": canvas_counts.get("classic", 0)},
    ]
    return {"categories": categories, "canvases": canvases, "items": items}


def check_canvas_assets(payload: CanvasAssetCheckRequest) -> dict[str, dict[str, bool]]:
    result: dict[str, bool] = {}
    for url in payload.urls[:3000]:
        text = str(url or "").strip()
        if not text:
            continue
        if text.startswith("/output/") or text.startswith("/assets/"):
            result[text] = bool(output_file_from_url(text))
        else:
            result[text] = True
    return {"exists": result}


def fetch_remote_media_bytes(
    url: str, timeout: float = 30.0, max_bytes: int = 200 * 1024 * 1024
) -> tuple[bytes, str] | None:
    text = str(url or "").strip()
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    with requests.get(text, stream=True, timeout=timeout, headers={"User-Agent": "ComfyUI-API-Modelscope/1.0"}) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type") or "application/octet-stream"
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(status_code=413, detail="文件太大，无法下载")
            chunks.append(chunk)
        return b"".join(chunks), content_type


def download_canvas_assets(payload: CanvasAssetDownloadRequest) -> Response:
    import zipfile

    buffer = BytesIO()
    used_names: set[str] = set()
    count = 0
    raw_items = payload.items or [{"url": url} for url in payload.urls]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for raw in raw_items[:1000]:
            if isinstance(raw, dict):
                text = str(raw.get("url") or "").strip()
                requested_name = str(raw.get("name") or "").strip()
            else:
                text = str(raw or "").strip()
                requested_name = ""
            if not text:
                continue
            path = output_file_from_url(text)
            content: bytes | None = None
            if path and path.is_file():
                base = sanitize_export_filename(
                    requested_name or path.name, path.name or f"image-{count + 1}.png"
                )
            else:
                local_by_name = local_media_file_by_basename(filename_from_media_url(text, ""))
                if local_by_name and local_by_name.is_file():
                    path = local_by_name
                    base = sanitize_export_filename(
                        requested_name or path.name, path.name or f"image-{count + 1}.png"
                    )
                else:
                    try:
                        remote = fetch_remote_media_bytes(text)
                    except Exception:
                        remote = None
                    if not remote:
                        continue
                    content, _content_type = remote
                    base = sanitize_export_filename(
                        requested_name or filename_from_media_url(text, f"image-{count + 1}.bin"),
                        f"image-{count + 1}.bin",
                    )
            name, ext = os.path.splitext(base)
            archive_name = base
            suffix = 2
            while archive_name in used_names:
                archive_name = f"{name}-{suffix}{ext}"
                suffix += 1
            used_names.add(archive_name)
            if path and path.is_file():
                zf.write(path, archive_name)
            elif content is not None:
                zf.writestr(archive_name, content)
            count += 1
    if count <= 0:
        raise HTTPException(status_code=404, detail="没有可下载的本地图片")
    buffer.seek(0)
    filename = re.sub(r'[\\/:*?"<>|]+', "_", payload.filename or "canvas-output-images.zip")
    if not filename.lower().endswith(".zip"):
        filename += ".zip"
    encoded = urllib.parse.quote(filename)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"}
    return Response(buffer.getvalue(), media_type="application/zip", headers=headers)
