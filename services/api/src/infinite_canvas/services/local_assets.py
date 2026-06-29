"""Local asset manager — upload, folders, caption, classify (legacy parity)."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.parse
import uuid
from typing import Any

import httpx
from fastapi import HTTPException, UploadFile
from PIL import Image

from infinite_canvas.core.asset_utils import normalize_asset_classification, sanitize_asset_name
from infinite_canvas.core.paths import local_upload_dir
from infinite_canvas.schemas.local_assets import (
    LocalAssetCaptionRequest,
    LocalAssetCaptionSaveRequest,
    LocalAssetClassifyRequest,
    LocalAssetFolderRequest,
    LocalAssetRenameRequest,
    LocalAssetUrlImportRequest,
)
from infinite_canvas.services import asset_ai

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov", ".m4v", ".flv"}
_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


def upload_root() -> str:
    return str(local_upload_dir())


def _local_upload_kind_ext(filename: str, content_type: str) -> tuple[str | None, str]:
    ext = os.path.splitext(filename or "")[1].lower()
    ct = (content_type or "").lower()
    if ext in _VIDEO_EXTS or ct.startswith("video/"):
        if ext not in _VIDEO_EXTS:
            ext = ".webm" if "webm" in ct else ".mov" if "quicktime" in ct else ".mp4"
        return "video", ext
    if ext in _AUDIO_EXTS or ct.startswith("audio/"):
        if ext not in _AUDIO_EXTS:
            ext = ".wav" if "wav" in ct else ".ogg" if "ogg" in ct else ".m4a" if "mp4" in ct else ".mp3"
        return "audio", ext
    if ext in _IMAGE_EXTS or ct.startswith("image/"):
        if ext not in _IMAGE_EXTS:
            ext = ".jpg" if "jpeg" in ct else ".webp" if "webp" in ct else ".gif" if "gif" in ct else ".png"
        return "image", ext
    return None, ext


def _local_upload_display_name(filename: str) -> str:
    base = os.path.basename(str(filename or ""))
    match = re.match(r"^up_[0-9a-f]{12}_(.+)$", base)
    return match.group(1) if match else base


def _local_upload_rel_path(value: str) -> str:
    text = str(value or "").replace("\\", "/").strip().lstrip("/")
    if not text:
        return ""
    norm = os.path.normpath(text).replace("\\", "/")
    if norm in {".", ""}:
        return ""
    if norm.startswith("../") or norm == ".." or os.path.isabs(norm):
        raise HTTPException(status_code=400, detail="非法路径")
    return norm


def _local_upload_abs(rel: str) -> tuple[str, str]:
    rel_path = _local_upload_rel_path(rel)
    path = os.path.abspath(os.path.join(upload_root(), rel_path))
    root = os.path.abspath(upload_root())
    try:
        common = os.path.commonpath([root, path])
    except ValueError:
        raise HTTPException(status_code=400, detail="非法路径") from None
    if common != root:
        raise HTTPException(status_code=400, detail="非法路径")
    return rel_path, path


def _local_upload_safe_path(name: str) -> tuple[str, str]:
    filename, path = _local_upload_abs(name)
    if not filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    return filename, path


def _local_upload_safe_folder(path_value: str) -> tuple[str, str]:
    return _local_upload_abs(path_value)


def _local_upload_safe_folder_name(name: str) -> str:
    cleaned = sanitize_asset_name(os.path.basename(str(name or "").strip()), "")
    cleaned = re.sub(r"[\\/]+", "_", cleaned).strip(" ._")
    if not cleaned:
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")
    return cleaned[:60]


def _local_upload_safe_file_stem(name: str) -> str:
    raw = os.path.splitext(os.path.basename(str(name or "").strip()))[0]
    cleaned = sanitize_asset_name(raw, "")
    cleaned = re.sub(r"[\\/]+", "_", cleaned).strip(" ._")
    if not cleaned:
        raise HTTPException(status_code=400, detail="文件名称不能为空")
    return cleaned[:120]


def _local_upload_caption_path(filename: str) -> str:
    return os.path.splitext(os.path.join(upload_root(), filename))[0] + ".txt"


def _local_upload_classification_path(filename: str) -> str:
    return os.path.splitext(os.path.join(upload_root(), filename))[0] + ".classification.json"


def _read_local_upload_caption(filename: str) -> tuple[str, str]:
    caption_path = _local_upload_caption_path(filename)
    if not os.path.isfile(caption_path):
        return "", ""
    try:
        with open(caption_path, encoding="utf-8-sig") as f:
            text = f.read()
    except UnicodeDecodeError:
        with open(caption_path, encoding="gb18030", errors="replace") as f:
            text = f.read()
    except OSError:
        return "", ""
    return text, os.path.basename(caption_path)


def _read_local_upload_classification(filename: str) -> dict[str, Any] | None:
    path = _local_upload_classification_path(filename)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return normalize_asset_classification(json.load(f))
    except Exception:
        return None


def _write_local_upload_classification(filename: str, classification: dict[str, Any]) -> None:
    path = _local_upload_classification_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(normalize_asset_classification(classification), f, ensure_ascii=False, indent=2)


def _sniff_image_ext_bytes(head: bytes) -> str | None:
    head = head or b""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if head[:2] == b"BM":
        return ".bmp"
    return None


def _local_upload_item(filename: str) -> dict[str, Any]:
    path = os.path.join(upload_root(), filename)
    rel = _local_upload_rel_path(filename)
    try:
        stat = os.stat(path)
        size = stat.st_size
        created_at = stat.st_mtime
    except OSError:
        size = 0
        created_at = 0
    kind, _ = _local_upload_kind_ext(filename, "")
    item: dict[str, Any] = {
        "id": rel,
        "file": rel,
        "name": _local_upload_display_name(rel),
        "url": f"/assets/uploads/{urllib.parse.quote(rel, safe='/')}",
        "kind": kind or "image",
        "size": size,
        "created_at": created_at,
        "folder": os.path.dirname(rel).replace("\\", "/"),
    }
    if kind == "image":
        try:
            with Image.open(path) as img:
                item["natural_w"], item["natural_h"] = img.size
                item["width"], item["height"] = img.size
        except Exception:
            pass
        caption, caption_file = _read_local_upload_caption(filename)
        item["caption"] = caption
        item["caption_file"] = caption_file
        classification = _read_local_upload_classification(filename)
        if classification:
            item["classification"] = classification
    return item


def _local_upload_folder_node(path: str = "", name: str = "全部上传") -> dict[str, Any]:
    rel = _local_upload_rel_path(path)
    return {
        "id": rel or "__root__",
        "path": rel,
        "name": name if not rel else os.path.basename(rel),
        "items": [],
        "children": [],
    }


def _local_upload_tree_and_items() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root_node = _local_upload_folder_node("", "全部上传")
    folder_map: dict[str, dict[str, Any]] = {"": root_node}
    items: list[dict[str, Any]] = []
    root = upload_root()
    if not os.path.isdir(root):
        return root_node, items
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted([d for d in dirs if not d.startswith(".") and not d.startswith("._")], key=str.lower)
        rel_dir = os.path.relpath(current, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        node = folder_map.get(rel_dir)
        if node is None:
            node = _local_upload_folder_node(rel_dir)
            folder_map[rel_dir] = node
        for dirname in dirs:
            child_rel = f"{rel_dir}/{dirname}".lstrip("/")
            child = _local_upload_folder_node(child_rel)
            folder_map[child_rel] = child
            node["children"].append(child)
        for name in sorted(files, key=str.lower):
            if name.startswith(".") or name.startswith("._"):
                continue
            rel_file = f"{rel_dir}/{name}".lstrip("/")
            kind, _ = _local_upload_kind_ext(name, "")
            if kind is None:
                continue
            item = _local_upload_item(rel_file)
            node["items"].append(item)
            items.append(item)

    def fill_counts(node: dict[str, Any]) -> int:
        total = len(node.get("items") or [])
        for child in node.get("children") or []:
            total += fill_counts(child)
        node["count"] = total
        return total

    fill_counts(root_node)
    items.sort(key=lambda it: it.get("created_at") or 0, reverse=True)
    return root_node, items


async def upload_local_assets(files: list[UploadFile], folder: str = "") -> dict[str, Any]:
    uploaded: list[dict[str, Any]] = []
    folder_rel, folder_abs = _local_upload_safe_folder(folder)
    os.makedirs(folder_abs, exist_ok=True)
    for file in files:
        content = await file.read()
        if not content:
            continue
        kind, ext = _local_upload_kind_ext(file.filename or "", file.content_type or "")
        if kind is None:
            continue
        base = os.path.splitext(os.path.basename(file.filename or "file"))[0]
        base = re.sub(r"[^0-9A-Za-z一-鿿._-]+", "_", base).strip("_") or "file"
        base = base[:60]
        filename = f"up_{uuid.uuid4().hex[:12]}_{base}{ext}"
        rel_name = f"{folder_rel}/{filename}".lstrip("/")
        path = os.path.join(folder_abs, filename)
        with open(path, "wb") as f:
            f.write(content)
        if kind == "image":
            classification = await asset_ai.classify_asset_image_best_effort(path)
            if classification:
                _write_local_upload_classification(rel_name, classification)
        uploaded.append(_local_upload_item(rel_name))
    return {"files": uploaded}


async def import_local_assets_from_urls(payload: LocalAssetUrlImportRequest) -> dict[str, Any]:
    uploaded: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    folder_rel, folder_abs = _local_upload_safe_folder(payload.folder)
    os.makedirs(folder_abs, exist_ok=True)
    timeout = httpx.Timeout(connect=20.0, read=120.0, write=30.0, pool=20.0)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "Infinite-Canvas-Asset-Importer/1.0"},
    ) as client:
        for entry in (payload.items or [])[:200]:
            src_url = str(entry.url or "").strip()
            inline_data = str(entry.data or "").strip()
            result: dict[str, Any] = {"url": src_url, "ok": False, "file": "", "error": ""}
            if not inline_data and not src_url.startswith(("http://", "https://")):
                result["error"] = "仅支持 http(s) 素材地址"
                results.append(result)
                continue
            try:
                if inline_data:
                    content_type = str(entry.content_type or "").split(";", 1)[0].strip().lower()
                    b64 = inline_data
                    if inline_data.startswith("data:"):
                        header, _, b64 = inline_data.partition(",")
                        if not content_type:
                            content_type = header[5:].split(";", 1)[0].strip().lower()
                    try:
                        content = base64.b64decode(b64, validate=False)
                    except Exception as exc:
                        raise HTTPException(status_code=400, detail="素材数据无法解码") from exc
                    name_path = urllib.parse.urlparse(src_url).path
                else:
                    response = await client.get(src_url)
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
                    content = response.content
                    name_path = urllib.parse.urlparse(src_url).path
                kind, ext = _local_upload_kind_ext(name_path, content_type)
                if kind == "image":
                    real = _sniff_image_ext_bytes(content[:16])
                    if real and not (real == ".jpg" and ext == ".jpeg"):
                        ext = real
                if kind not in ("image", "video"):
                    raise HTTPException(status_code=400, detail=f"不是图片或视频资源：{content_type or src_url}")
                if not content:
                    raise HTTPException(status_code=400, detail="素材内容为空")
                if entry.name:
                    base = os.path.splitext(entry.name)[0]
                else:
                    base = os.path.splitext(os.path.basename(urllib.parse.unquote(name_path)))[0]
                base = base or ("web-video" if kind == "video" else "web-image")
                base = re.sub(r"[^0-9A-Za-z一-鿿._-]+", "_", base).strip("_") or (
                    "web-video" if kind == "video" else "web-image"
                )
                base = base[:60]
                if ext and base.lower().endswith(ext.lower()):
                    base = base[: -len(ext)].rstrip(".") or ("web-video" if kind == "video" else "web-image")
                filename = f"up_{uuid.uuid4().hex[:12]}_{base}{ext}"
                rel_name = f"{folder_rel}/{filename}".lstrip("/")
                path = os.path.join(folder_abs, filename)
                with open(path, "wb") as f:
                    f.write(content)
                if payload.classify and kind == "image":
                    classification = await asset_ai.classify_asset_image_best_effort(
                        path,
                        payload.provider,
                        payload.model,
                        payload.ms_model,
                        payload.prompt,
                    )
                    if classification:
                        _write_local_upload_classification(rel_name, classification)
                item = _local_upload_item(rel_name)
                uploaded.append(item)
                result.update({"ok": True, "file": rel_name, "item": item})
            except HTTPException as exc:
                result["error"] = str(exc.detail or "导入失败")
            except Exception as exc:
                result["error"] = str(exc) or "导入失败"
            results.append(result)
    return {"ok": True, "count": len(uploaded), "files": uploaded, "items": results}


def list_local_assets() -> dict[str, Any]:
    tree, items = _local_upload_tree_and_items()
    return {"items": items, "tree": tree}


def create_local_asset_folder(payload: LocalAssetFolderRequest) -> dict[str, Any]:
    parent_rel, parent_abs = _local_upload_safe_folder(payload.parent)
    if not os.path.isdir(parent_abs):
        raise HTTPException(status_code=404, detail="父文件夹不存在")
    name = _local_upload_safe_folder_name(payload.name)
    rel = f"{parent_rel}/{name}".lstrip("/")
    _, abs_path = _local_upload_safe_folder(rel)
    if os.path.exists(abs_path):
        raise HTTPException(status_code=400, detail="同名文件夹已存在")
    os.makedirs(abs_path, exist_ok=False)
    tree, items = _local_upload_tree_and_items()
    return {"ok": True, "folder": {"path": rel, "name": name}, "tree": tree, "items": items}


def rename_local_asset_folder(payload: LocalAssetFolderRequest) -> dict[str, Any]:
    rel, abs_path = _local_upload_safe_folder(payload.path)
    if not rel:
        raise HTTPException(status_code=400, detail="根目录不能重命名")
    if not os.path.isdir(abs_path):
        raise HTTPException(status_code=404, detail="文件夹不存在")
    name = _local_upload_safe_folder_name(payload.name)
    parent = os.path.dirname(rel).replace("\\", "/")
    new_rel = f"{parent}/{name}".lstrip("/")
    _, new_abs = _local_upload_safe_folder(new_rel)
    if os.path.exists(new_abs):
        raise HTTPException(status_code=400, detail="同名文件夹已存在")
    os.rename(abs_path, new_abs)
    tree, items = _local_upload_tree_and_items()
    return {"ok": True, "folder": {"path": new_rel, "name": name}, "tree": tree, "items": items}


def rename_local_asset_item(payload: LocalAssetRenameRequest) -> dict[str, Any]:
    rel, abs_path = _local_upload_safe_path(payload.path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="本地素材不存在")
    kind, ext = _local_upload_kind_ext(rel, "")
    if kind is None:
        raise HTTPException(status_code=400, detail="不支持的素材类型")
    new_stem = _local_upload_safe_file_stem(payload.name)
    old_ext = os.path.splitext(rel)[1] or ext
    parent = os.path.dirname(rel).replace("\\", "/")
    new_rel = f"{parent}/{new_stem}{old_ext}".lstrip("/")
    if new_rel == rel:
        tree, items = _local_upload_tree_and_items()
        return {"ok": True, "item": _local_upload_item(rel), "tree": tree, "items": items}
    _, new_abs = _local_upload_abs(new_rel)
    if os.path.exists(new_abs):
        raise HTTPException(status_code=400, detail="同名素材已存在")
    os.rename(abs_path, new_abs)
    old_caption = _local_upload_caption_path(rel)
    new_caption = _local_upload_caption_path(new_rel)
    if os.path.isfile(old_caption) and not os.path.exists(new_caption):
        os.rename(old_caption, new_caption)
    old_classification = _local_upload_classification_path(rel)
    new_classification = _local_upload_classification_path(new_rel)
    if os.path.isfile(old_classification) and not os.path.exists(new_classification):
        os.rename(old_classification, new_classification)
    tree, items = _local_upload_tree_and_items()
    return {"ok": True, "item": _local_upload_item(new_rel), "old_path": rel, "tree": tree, "items": items}


def delete_local_assets(names: list[str]) -> dict[str, Any]:
    deleted: list[str] = []
    for name in names:
        try:
            rel, path = _local_upload_safe_path(name)
        except HTTPException:
            continue
        if os.path.isfile(path):
            try:
                os.remove(path)
                txt_path = _local_upload_caption_path(rel)
                if os.path.isfile(txt_path):
                    os.remove(txt_path)
                cls_path = _local_upload_classification_path(rel)
                if os.path.isfile(cls_path):
                    os.remove(cls_path)
                deleted.append(rel)
            except OSError:
                pass
    return {"deleted": deleted}


def move_local_assets(names: list[str], folder: str = "") -> dict[str, Any]:
    if not names:
        raise HTTPException(status_code=400, detail="没有选择素材")
    target_rel, target_abs = _local_upload_safe_folder(folder)
    if target_rel and not os.path.isdir(target_abs):
        raise HTTPException(status_code=404, detail="目标文件夹不存在")
    moved = 0
    for name in names:
        try:
            rel, abs_path = _local_upload_safe_path(name)
        except HTTPException:
            continue
        if not os.path.isfile(abs_path):
            continue
        base = os.path.basename(rel)
        new_rel = f"{target_rel}/{base}".lstrip("/") if target_rel else base
        if new_rel == rel:
            continue
        _, new_abs = _local_upload_abs(new_rel)
        if os.path.exists(new_abs):
            stem, ext = os.path.splitext(base)
            base = f"{stem}_{uuid.uuid4().hex[:6]}{ext}"
            new_rel = f"{target_rel}/{base}".lstrip("/") if target_rel else base
            _, new_abs = _local_upload_abs(new_rel)
        try:
            os.makedirs(os.path.dirname(new_abs), exist_ok=True)
            os.rename(abs_path, new_abs)
            for src_sib, dst_sib in (
                (_local_upload_caption_path(rel), _local_upload_caption_path(new_rel)),
                (_local_upload_classification_path(rel), _local_upload_classification_path(new_rel)),
            ):
                if os.path.isfile(src_sib) and not os.path.exists(dst_sib):
                    os.rename(src_sib, dst_sib)
            moved += 1
        except OSError:
            continue
    tree, items = _local_upload_tree_and_items()
    return {"ok": True, "moved": moved, "items": items, "tree": tree}


async def caption_local_assets(payload: LocalAssetCaptionRequest) -> dict[str, Any]:
    prompt = (payload.prompt or "描述图片").strip() or "描述图片"
    items: list[dict[str, Any]] = []
    ok_count = 0
    for name in (payload.names or [])[:100]:
        item: dict[str, Any] = {"name": name, "ok": False, "caption": "", "caption_file": "", "error": ""}
        try:
            filename, path = _local_upload_safe_path(name)
            if not os.path.isfile(path):
                raise HTTPException(status_code=404, detail="文件不存在")
            kind, _ = _local_upload_kind_ext(filename, "")
            if kind != "image":
                raise HTTPException(status_code=400, detail="仅支持图片素材反推提示词")
            caption, resolved_model = await asset_ai.caption_image_with_provider(
                path,
                prompt,
                payload.provider,
                payload.model,
                payload.ms_model,
            )
            txt_path = _local_upload_caption_path(filename)
            with open(txt_path, "w", encoding="utf-8", newline="") as f:
                f.write(caption)
            item.update(
                {
                    "ok": True,
                    "name": filename,
                    "caption": caption,
                    "caption_file": os.path.basename(txt_path),
                    "model": resolved_model,
                }
            )
            ok_count += 1
        except HTTPException as exc:
            item["error"] = str(exc.detail or "反推失败")
        except Exception as exc:
            item["error"] = str(exc) or "反推失败"
        items.append(item)
    return {"ok": True, "count": ok_count, "items": items}


async def classify_local_assets(payload: LocalAssetClassifyRequest) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    ok_count = 0
    for name in (payload.names or [])[:80]:
        item: dict[str, Any] = {
            "name": name,
            "ok": False,
            "classification": None,
            "classification_file": "",
            "error": "",
        }
        try:
            filename, path = _local_upload_safe_path(name)
            if not os.path.isfile(path):
                raise HTTPException(status_code=404, detail="文件不存在")
            kind, _ = _local_upload_kind_ext(filename, "")
            if kind != "image":
                raise HTTPException(status_code=400, detail="仅支持图片素材智能分类")
            classification = await asset_ai.classify_image_with_provider(
                path,
                payload.provider,
                payload.model,
                payload.ms_model,
                payload.prompt,
            )
            _write_local_upload_classification(filename, classification)
            item.update(
                {
                    "ok": True,
                    "name": filename,
                    "classification": classification,
                    "classification_file": os.path.basename(_local_upload_classification_path(filename)),
                    "model": classification.get("model") or "",
                }
            )
            ok_count += 1
        except HTTPException as exc:
            item["error"] = str(exc.detail or "智能分类失败")
        except Exception as exc:
            item["error"] = str(exc) or "智能分类失败"
        items.append(item)
    return {"ok": True, "count": ok_count, "items": items}


def save_local_asset_caption(payload: LocalAssetCaptionSaveRequest) -> dict[str, Any]:
    filename, path = _local_upload_safe_path(payload.name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="文件不存在")
    kind, _ = _local_upload_kind_ext(filename, "")
    if kind != "image":
        raise HTTPException(status_code=400, detail="仅支持图片素材保存提示词")
    caption = str(payload.caption or "")[:100000]
    txt_path = _local_upload_caption_path(filename)
    with open(txt_path, "w", encoding="utf-8", newline="") as f:
        f.write(caption)
    return {"ok": True, "caption": caption, "caption_file": os.path.basename(txt_path)}
