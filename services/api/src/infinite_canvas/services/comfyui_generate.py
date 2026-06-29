"""ComfyUI generation, canvas tasks, and image param schema — legacy parity."""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from threading import Lock
from typing import Any

import requests
from PIL import Image

from infinite_canvas.core.comfyui import (
    collect_required_comfy_media,
    comfyui_instances,
    release_backend_load,
    reserve_best_backend,
)
from infinite_canvas.core.media import output_path_for, output_url_for, sanitize_export_filename
from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.queue import NEXT_TASK_ID, QUEUE, QUEUE_LOCK
from infinite_canvas.core.websocket import GLOBAL_LOOP, manager
from infinite_canvas.schemas.comfyui import GenerateRequest
from infinite_canvas.services import comfyui_workflows, history as history_service
from infinite_canvas.services.asset_ai import is_volcengine_provider
from infinite_canvas.services import provider_store

CLIENT_ID = str(uuid.uuid4())
COMFYUI_HISTORY_TIMEOUT = int(float(os.getenv("COMFYUI_HISTORY_TIMEOUT", "1800")))
COMFYUI_DOWNLOAD_TIMEOUT = float(os.getenv("COMFYUI_DOWNLOAD_TIMEOUT", "120"))
ONLINE_IMAGE_REFERENCE_MAX = int(os.getenv("ONLINE_IMAGE_REFERENCE_MAX", "20"))

CANVAS_TASKS: dict[str, dict[str, Any]] = {}
CANVAS_TASK_LOCK = Lock()

IMAGE_PARAM_RATIOS = [
    {"value": "1:1", "label": "1:1"},
    {"value": "3:4", "label": "3:4"},
    {"value": "4:3", "label": "4:3"},
    {"value": "16:9", "label": "16:9"},
    {"value": "9:16", "label": "9:16"},
    {"value": "2:3", "label": "2:3"},
    {"value": "3:2", "label": "3:2"},
]
IMAGE_PARAM_RESOLUTIONS = [
    {"value": "1k", "label": "1K"},
    {"value": "2k", "label": "2K"},
    {"value": "4k", "label": "4K"},
]

COMFY_PREVIEW_CLASS_HINTS = ("previewimage", "comparer", "imagecompare", "image compare")
COMFY_DEBUG_TEXT_CLASS_HINTS = (
    "showtext",
    "show text",
    "showanything",
    "show any",
    "preview any",
    "previewany",
    "displaytext",
    "display text",
    "display any",
    "anything everywhere",
    "convertanything",
    "easy show",
    "note",
    "mathexpression",
    "cr text",
    "text multiline",
    "string function",
    "debug",
)


def is_runninghub_provider(provider: dict[str, Any] | None) -> bool:
    return (
        provider_store.provider_protocol(provider) == "runninghub"
        or str((provider or {}).get("id") or "").strip().lower() == "runninghub"
    )


def is_gpt_image_2_model(model: str) -> bool:
    raw = str(model or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    compact = re.sub(r"[^a-z0-9]+", "", raw)
    return (
        normalized == "gpt-image-2"
        or normalized.startswith("gpt-image-2-")
        or normalized.endswith("-gpt-image-2")
        or "-gpt-image-2-" in normalized
        or compact == "gptimage2"
        or compact.startswith("gptimage2")
        or compact.endswith("gptimage2")
    )


def build_image_param_fields(engine: str, provider: dict[str, Any], model: str) -> list[dict[str, Any]]:
    gpt_auto_size = engine == "api" and is_gpt_image_2_model(model)
    image_resolutions = (
        [{"value": "auto", "label": "自动"}] + IMAGE_PARAM_RESOLUTIONS
        if gpt_auto_size
        else IMAGE_PARAM_RESOLUTIONS
    )
    size_field = {
        "key": "size",
        "type": "size",
        "label": "尺寸",
        "ratios": IMAGE_PARAM_RATIOS,
        "resolutions": image_resolutions,
        "default": {"ratio": "1:1", "resolution": "auto" if gpt_auto_size else "1k"},
    }
    count_field = {
        "key": "n",
        "type": "int",
        "label": "数量",
        "control": "chips",
        "options": [1, 2, 3, 4],
        "default": 1,
    }
    refs_field = {
        "key": "reference_images",
        "type": "refs",
        "label": "参考图",
        "max": ONLINE_IMAGE_REFERENCE_MAX,
    }
    if engine == "runninghub":
        return [
            {
                "key": "_rh_notice",
                "type": "notice",
                "label": "RunningHub 工作流参数将按所选工作流动态加载（开发中）。",
            }
        ]
    fields: list[dict[str, Any]] = [size_field]
    if engine in ("api", "volcengine"):
        fields.append(
            {
                "key": "quality",
                "type": "select",
                "label": "质量",
                "control": "chips",
                "options": [
                    {"value": "auto", "label": "自动"},
                    {"value": "low", "label": "低"},
                    {"value": "medium", "label": "中"},
                    {"value": "high", "label": "高"},
                ],
                "default": "auto",
            }
        )
    fields.append(count_field)
    fields.append(refs_field)
    return fields


def image_params(provider_id: str = "", model: str = "") -> dict[str, Any]:
    providers = provider_store.load_api_providers()
    provider = (
        next((p for p in providers if p.get("id") == (provider_id or "").strip().lower()), None) or {}
    )
    if is_runninghub_provider(provider):
        engine = "runninghub"
    elif (provider_id or "").strip().lower() == "modelscope":
        engine = "modelscope"
    elif is_volcengine_provider(provider):
        engine = "volcengine"
    else:
        engine = "api"
    return {
        "engine": engine,
        "submit": "/api/canvas-image-tasks",
        "fields": build_image_param_fields(engine, provider, model),
    }


def comfy_output_extension(item: dict[str, Any]) -> str:
    filename = str((item or {}).get("filename") or "")
    ext = os.path.splitext(filename)[1].lower()
    allowed = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".mp4",
        ".webm",
        ".mov",
        ".m4v",
        ".avi",
        ".mkv",
        ".mp3",
        ".wav",
        ".m4a",
        ".aac",
        ".ogg",
        ".flac",
        ".txt",
        ".json",
        ".csv",
        ".srt",
        ".vtt",
        ".md",
    }
    if ext in allowed:
        return ext
    fmt = str((item or {}).get("format") or "").lower()
    if "mpeg" in fmt or "mp3" in fmt:
        return ".mp3"
    if "wav" in fmt or "wave" in fmt:
        return ".wav"
    if "ogg" in fmt:
        return ".ogg"
    if "flac" in fmt:
        return ".flac"
    if "text" in fmt or "plain" in fmt:
        return ".txt"
    if "json" in fmt:
        return ".json"
    if "webm" in fmt:
        return ".webm"
    if "quicktime" in fmt or "mov" in fmt:
        return ".mov"
    if "mp4" in fmt or "h264" in fmt or "video" in fmt:
        return ".mp4"
    return ext or ".bin"


def comfy_output_kind(item: dict[str, Any]) -> str:
    ext = comfy_output_extension(item)
    fmt = str((item or {}).get("format") or "").lower()
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"} or "image" in fmt:
        return "image"
    if ext in {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"} or "video" in fmt:
        return "video"
    if ext in {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"} or "audio" in fmt or "sound" in fmt:
        return "audio"
    if ext in {".txt", ".json", ".csv", ".srt", ".vtt", ".md"} or "text" in fmt or "json" in fmt:
        return "text"
    return "file"


def comfy_class_is_preview(class_type: str) -> bool:
    ct = str(class_type or "").lower()
    return bool(ct) and any(h in ct for h in COMFY_PREVIEW_CLASS_HINTS)


def comfy_class_is_debug_text(class_type: str) -> bool:
    ct = str(class_type or "").lower()
    return bool(ct) and any(h in ct for h in COMFY_DEBUG_TEXT_CLASS_HINTS)


def collect_comfy_file_items(node_output: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    items: list[tuple[str, dict[str, Any]]] = []
    for key, value in (node_output or {}).items():
        if key in {"text", "texts", "prompt", "prompts", "string", "strings", "caption", "captions"}:
            continue
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            if isinstance(item, dict) and item.get("filename"):
                items.append((key, item))
    return items


def comfy_text_values_from_output(node_output: dict[str, Any]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    text_keys = ("text", "texts", "prompt", "prompts", "string", "strings", "caption", "captions")
    for key in text_keys:
        if key not in node_output:
            continue
        value = node_output.get(key)
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, dict):
                text = item.get("text") or item.get("prompt") or item.get("caption") or item.get("value")
                name = item.get("filename") or item.get("name") or f"{key}.txt"
            else:
                text = item
                name = f"{key}.txt"
            if text is None:
                continue
            text = str(text)
            if text.strip():
                values.append((text, str(name)))
    return values


def download_comfy_output(comfy_address: str, item: dict[str, Any], prefix: str = "studio_") -> str:
    ext = comfy_output_extension(item)
    filename = f"{prefix}{uuid.uuid4().hex[:10]}{ext}"
    local_path = output_path_for(filename, "output")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    subfolder = urllib.parse.quote(str(item.get("subfolder") or ""))
    file_type = urllib.parse.quote(str(item.get("type") or "output"))
    comfy_url_path = (
        f"/view?filename={urllib.parse.quote(str(item['filename']))}"
        f"&subfolder={subfolder}&type={file_type}"
    )
    full_url = f"http://{comfy_address}{comfy_url_path}"
    try:
        with (
            urllib.request.urlopen(full_url, timeout=COMFYUI_DOWNLOAD_TIMEOUT) as response,
            open(local_path, "wb") as out_file,
        ):
            shutil.copyfileobj(response, out_file)
        return output_url_for(filename, "output")
    except Exception as exc:
        print(f"下载 ComfyUI 输出失败: {exc}")
        if comfy_url_path.startswith("/view"):
            return comfy_url_path.replace("/view", "/api/view", 1)
        return full_url


def save_comfy_text_output(value: Any, prefix: str = "studio_", name: str = "") -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)
    stem = sanitize_export_filename(name or "comfy_text.txt", "comfy_text.txt")
    _, ext = os.path.splitext(stem)
    if ext.lower() not in {".txt", ".json", ".csv", ".srt", ".vtt", ".md"}:
        stem += ".txt"
    filename = f"{prefix}{uuid.uuid4().hex[:10]}_{stem}"
    path = output_path_for(filename, "output")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return output_url_for(filename, "output")


def convert_output_to_jpg(url: str, quality: int = 88) -> str:
    path = output_file_from_url(url)
    if not path:
        return url
    root, ext = os.path.splitext(str(path))
    if ext.lower() in [".jpg", ".jpeg"]:
        return url
    jpg_path = f"{root}.jpg"
    try:
        with Image.open(path) as img:
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            img.save(jpg_path, "JPEG", quality=quality, optimize=True)
        rel = os.path.relpath(jpg_path, path.parent.parent).replace("\\", "/")
        return f"/assets/{rel}"
    except Exception as exc:
        print(f"转换 JPG 失败: {exc}")
        return url


def get_comfy_history(comfy_address: str, prompt_id: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(f"http://{comfy_address}/history/{prompt_id}") as response:
            return json.loads(response.read())
    except Exception as exc:
        print(f"ComfyUI history error: {exc}")
        return {}


def _broadcast_new_image(result: dict[str, Any]) -> None:
    if GLOBAL_LOOP:
        asyncio.run_coroutine_threadsafe(manager.broadcast_new_image(result), GLOBAL_LOOP)


def generate(req: GenerateRequest) -> dict[str, Any]:
    global NEXT_TASK_ID
    current_task: dict[str, Any] | None = None
    target_backend: str | None = None
    with QUEUE_LOCK:
        task_id = NEXT_TASK_ID
        NEXT_TASK_ID += 1
        current_task = {"task_id": task_id, "client_id": req.client_id}
        QUEUE.append(current_task)

    try:
        required_images = collect_required_comfy_media(req.params)
        target_backend = reserve_best_backend(required_images)

        for image_name in required_images:
            need_sync = False
            try:
                check_url = (
                    f"http://{target_backend}/view?filename={urllib.parse.quote(image_name)}&type=input"
                )
                resp = requests.get(check_url, stream=True, timeout=0.5)
                resp.close()
                if resp.status_code != 200:
                    need_sync = True
            except Exception:
                need_sync = True

            if need_sync:
                image_content = None
                image_type = "image/png"
                for addr in comfyui_instances():
                    if addr == target_backend:
                        continue
                    try:
                        src_url = (
                            f"http://{addr}/view?filename={urllib.parse.quote(image_name)}&type=input"
                        )
                        r = requests.get(src_url, timeout=5)
                        if r.status_code == 200:
                            image_content = r.content
                            image_type = r.headers.get("Content-Type", "image/png")
                            break
                    except Exception:
                        continue

                if image_content:
                    try:
                        files = {"image": (image_name, image_content, image_type)}
                        requests.post(
                            f"http://{target_backend}/upload/image", files=files, timeout=10
                        )
                    except Exception as exc:
                        print(f"Sync upload failed: {exc}")

        workflow_path = comfyui_workflows.resolve_workflow_file(req.workflow_json)
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        seed = random.randint(1, 4294967295)

        if "23" in workflow and req.prompt:
            workflow["23"]["inputs"]["text"] = req.prompt
        if "144" in workflow:
            workflow["144"]["inputs"]["width"] = req.width
            workflow["144"]["inputs"]["height"] = req.height
        if "22" in workflow:
            workflow["22"]["inputs"]["seed"] = seed
        if "158" in workflow:
            workflow["158"]["inputs"]["noise_seed"] = seed
        for node_id in ["146", "181"]:
            if node_id in workflow and "inputs" in workflow[node_id] and "seed" in workflow[node_id]["inputs"]:
                workflow[node_id]["inputs"]["seed"] = seed
        if "184" in workflow and "inputs" in workflow["184"] and "seed" in workflow["184"]["inputs"]:
            workflow["184"]["inputs"]["seed"] = seed
        if "172" in workflow and "inputs" in workflow["172"] and "seed" in workflow["172"]["inputs"]:
            workflow["172"]["inputs"]["seed"] = seed
        if "14" in workflow and "inputs" in workflow["14"] and "seed" in workflow["14"]["inputs"]:
            workflow["14"]["inputs"]["seed"] = seed

        for node_id, node_inputs in req.params.items():
            if node_id in workflow:
                if "inputs" not in workflow[node_id]:
                    workflow[node_id]["inputs"] = {}
                for input_name, value in node_inputs.items():
                    workflow[node_id]["inputs"][input_name] = value

        p = {"prompt": workflow, "client_id": CLIENT_ID}
        data = json.dumps(p).encode("utf-8")
        try:
            post_req = urllib.request.Request(f"http://{target_backend}/prompt", data=data)
            prompt_id = json.loads(urllib.request.urlopen(post_req, timeout=10).read())["prompt_id"]
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8")
            raise RuntimeError(f"HTTP Error {exc.code}: {error_body}") from exc

        history_data = None
        for _ in range(COMFYUI_HISTORY_TIMEOUT):
            try:
                res = get_comfy_history(target_backend, prompt_id)
                if prompt_id in res:
                    history_data = res[prompt_id]
                    break
            except Exception:
                pass
            time.sleep(1)

        if not history_data:
            raise RuntimeError("ComfyUI 渲染超时")

        local_images: list[str] = []
        local_videos: list[str] = []
        local_audios: list[str] = []
        local_texts: list[str] = []
        local_files: list[str] = []
        local_items: list[dict[str, Any]] = []
        local_urls: list[str] = []
        current_timestamp = time.time()
        if "outputs" in history_data:
            workflow_nodes = workflow if isinstance(workflow, dict) else {}

            def _class_type_of(nid: str) -> str:
                node_def = workflow_nodes.get(str(nid))
                return str(node_def.get("class_type") or "") if isinstance(node_def, dict) else ""

            file_candidates: list[tuple[str, str, str, dict[str, Any], str]] = []
            text_candidates: list[tuple[str, str, str, str]] = []
            for node_id in history_data["outputs"]:
                node_output = history_data["outputs"][node_id]
                class_type = _class_type_of(node_id)
                for output_key, item in collect_comfy_file_items(node_output):
                    file_candidates.append(
                        (node_id, class_type, output_key, item, comfy_output_kind(item))
                    )
                for text, name in comfy_text_values_from_output(node_output):
                    text_candidates.append((node_id, class_type, text, name))

            has_primary_image = any(
                kind == "image" and not comfy_class_is_preview(ct)
                for (_nid, ct, _ok, _it, kind) in file_candidates
            )
            prefix = f"{req.type}_{int(current_timestamp)}_"
            for node_id, class_type, output_key, item, kind in file_candidates:
                if kind == "image" and has_primary_image and comfy_class_is_preview(class_type):
                    continue
                local_path = download_comfy_output(target_backend, item, prefix=prefix)
                if kind == "image" and req.convert_to_jpg:
                    local_path = convert_output_to_jpg(local_path)
                name = (
                    os.path.basename(str(item.get("filename") or ""))
                    or os.path.basename(str(local_path).split("?", 1)[0])
                )
                entry = {
                    "url": local_path,
                    "kind": kind,
                    "name": name,
                    "node_id": str(node_id),
                    "output_key": str(output_key),
                    "class_type": class_type,
                }
                if kind == "image":
                    local_images.append(local_path)
                elif kind == "video":
                    local_videos.append(local_path)
                elif kind == "audio":
                    local_audios.append(local_path)
                elif kind == "text":
                    local_texts.append(local_path)
                else:
                    local_files.append(local_path)
                local_items.append(entry)
                local_urls.append(local_path)

            for node_id, class_type, text, name in text_candidates:
                if comfy_class_is_debug_text(class_type):
                    continue
                local_path = save_comfy_text_output(text, prefix=prefix, name=name)
                entry = {
                    "url": local_path,
                    "kind": "text",
                    "name": os.path.basename(str(local_path).split("?", 1)[0]),
                    "node_id": str(node_id),
                    "output_key": "text",
                    "class_type": class_type,
                }
                local_texts.append(local_path)
                local_items.append(entry)
                local_urls.append(local_path)

        result = {
            "prompt": req.prompt if req.prompt else "Detail Enhance",
            "images": local_images,
            "videos": local_videos,
            "audios": local_audios,
            "texts": local_texts,
            "files": local_files,
            "items": local_items,
            "outputs": local_urls,
            "seed": seed,
            "timestamp": current_timestamp,
            "type": req.type,
            "workflow_json": req.workflow_json,
            "task_id": task_id,
            "prompt_id": prompt_id,
            "backend": target_backend,
            "params": req.params,
        }
        history_service.save_to_history(result)
        _broadcast_new_image(result)
        return result

    except Exception as exc:
        return {"images": [], "error": str(exc)}
    finally:
        if target_backend:
            release_backend_load(target_backend)
        if current_task:
            with QUEUE_LOCK:
                if current_task in QUEUE:
                    QUEUE.remove(current_task)


def workflow_run_params(payload_fields: dict[str, Any], config_fields: list[Any]) -> dict[str, dict[str, Any]]:
    params: dict[str, dict[str, Any]] = {}
    for field in config_fields:
        node = getattr(field, "node", None) or (field.get("node") if isinstance(field, dict) else "")
        input_name = getattr(field, "input", None) or (field.get("input") if isinstance(field, dict) else "")
        field_id = getattr(field, "id", None) or (field.get("id") if isinstance(field, dict) else "")
        field_type = getattr(field, "type", None) or (field.get("type") if isinstance(field, dict) else "text")
        step = getattr(field, "step", None) if not isinstance(field, dict) else field.get("step")
        if not node or not input_name:
            continue
        if field_id not in payload_fields:
            continue
        value = payload_fields[field_id]
        if field_type in ("number", "slider"):
            try:
                value = float(value) if (step and step < 1) else int(float(value))
            except Exception:
                pass
        elif field_type == "boolean":
            value = bool(value)
        elif field_type == "dropdown" and isinstance(value, str):
            s = value.strip()
            try:
                if s and ("." in s or "e" in s.lower()):
                    value = float(s)
                elif s and s.lstrip("-").isdigit():
                    value = int(s)
            except (ValueError, TypeError):
                pass
        params.setdefault(str(node), {})[str(input_name)] = value
    return params


async def run_canvas_comfy_task(task_id: str, payload: GenerateRequest) -> None:
    with CANVAS_TASK_LOCK:
        if task_id in CANVAS_TASKS:
            CANVAS_TASKS[task_id]["status"] = "running"
            CANVAS_TASKS[task_id]["updated_at"] = time.time()
    try:
        result = await asyncio.to_thread(generate, payload)
        if isinstance(result, dict) and result.get("error"):
            raise RuntimeError(str(result.get("error") or "ComfyUI 生成失败"))
        with CANVAS_TASK_LOCK:
            CANVAS_TASKS[task_id].update(
                {
                    "status": "succeeded",
                    "result": result,
                    "error": "",
                    "updated_at": time.time(),
                }
            )
    except Exception as exc:
        detail = getattr(exc, "detail", None) or str(exc)
        status_code = getattr(exc, "status_code", 500)
        with CANVAS_TASK_LOCK:
            CANVAS_TASKS[task_id].update(
                {
                    "status": "failed",
                    "error": str(detail),
                    "status_code": status_code,
                    "updated_at": time.time(),
                }
            )


def create_canvas_comfy_task(payload: GenerateRequest) -> dict[str, str]:
    task_id = f"canvas_comfy_{uuid.uuid4().hex}"
    with CANVAS_TASK_LOCK:
        CANVAS_TASKS[task_id] = {
            "id": task_id,
            "type": "comfy",
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),
            "result": None,
            "error": "",
            "workflow_json": payload.workflow_json,
        }
    return {"task_id": task_id, "status": "queued"}


def get_canvas_comfy_task(task_id: str) -> dict[str, Any]:
    with CANVAS_TASK_LOCK:
        task = dict(CANVAS_TASKS.get(task_id) or {})
    return task


def upload_comfyui_base64(data: str, name: str, content_type: str) -> dict[str, str]:
    import base64

    from infinite_canvas.services.local_assets import _local_upload_kind_ext

    raw = (data or "").strip()
    ct = (content_type or "").split(";", 1)[0].strip().lower()
    if raw.startswith("data:"):
        header, _, raw = raw.partition(",")
        if not ct:
            ct = header[5:].split(";", 1)[0].strip().lower()
    try:
        content = base64.b64decode(raw, validate=False)
    except Exception as exc:
        raise ValueError("数据无法解码") from exc
    if not content:
        raise ValueError("内容为空")
    _, ext = _local_upload_kind_ext(name or "", ct or "image/png")
    filename = f"dx_{uuid.uuid4().hex[:12]}{ext or '.png'}"
    comfy_name = None
    for addr in comfyui_instances():
        try:
            resp = requests.post(
                f"http://{addr}/upload/image",
                files={"image": (filename, content, ct or "image/png")},
                timeout=10,
            )
            if resp.status_code == 200:
                comfy_name = resp.json().get("name", filename)
        except Exception as exc:
            print(f"ComfyUI base64 upload error for {addr}: {exc}")
    if not comfy_name:
        raise RuntimeError("上传到 ComfyUI 失败")
    return {"name": comfy_name}
