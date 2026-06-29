"""RunningHub OpenAPI provider image/video — legacy parity."""

from __future__ import annotations

import math
import os
import time
from typing import Any

import httpx
from fastapi import HTTPException

from infinite_canvas.core.media import content_type_for_path
from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.provider_constants import RUNNINGHUB_DEFAULT_IMAGE_MODELS
from infinite_canvas.schemas.canvas_ai import CanvasVideoRequest
from infinite_canvas.services import provider_probe, provider_store, runninghub
from infinite_canvas.services.comfyui_generate import is_runninghub_provider
from infinite_canvas.services.jimeng import save_remote_video_to_output
from infinite_canvas.services.online_image import ONLINE_IMAGE_REFERENCE_MAX, extract_image
from infinite_canvas.services.provider_helpers import parse_size_pair, video_output_urls
from infinite_canvas.services.provider_probe import runninghub_openapi_base_url

def runninghub_openapi_url(provider, path=""):
    path = str(path or "").strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    path = path.lstrip("/")
    base = runninghub_openapi_base_url(provider)
    return f"{base}/{path}" if path else base


def runninghub_json_headers(provider):
    return runninghub_api_headers(provider)


def runninghub_api_headers(provider):
    api_key = str((provider or {}).get("api_key") or "").strip() or runninghub.runninghub_api_key(provider)
    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 RunningHub API Key，请在 API 设置中填写。")
    return {"Authorization": provider_store.bearer_auth_value(api_key), "Accept": "application/json", "Content-Type": "application/json"}


def runninghub_task_endpoint(provider, model):
    model_path = str(model or "").strip().strip("/")
    if not model_path:
        model_path = RUNNINGHUB_DEFAULT_IMAGE_MODELS[0]
    if model_path.startswith("/openapi/"):
        return runninghub.runninghub_endpoint_url(provider, model_path)
    if model_path.startswith("openapi/"):
        return runninghub.runninghub_endpoint_url(provider, f"/{model_path}")
    return runninghub_openapi_url(provider, model_path)


async def runninghub_model_definition(provider, model):
    requested = str(model or "").strip().strip("/")
    registry = await provider_probe.fetch_runninghub_model_registry(provider, include_fallback=True)
    for item in registry:
        mid = provider_probe.runninghub_model_id(item)
        endpoint = str(item.get("endpoint") or "").strip().strip("/")
        if requested and requested in {mid, endpoint, f"/openapi/v2/{endpoint}", f"openapi/v2/{endpoint}"}:
            return item
    endpoint = requested
    if endpoint.startswith("/openapi/v2/"):
        endpoint = endpoint[len("/openapi/v2/"):]
    elif endpoint.startswith("openapi/v2/"):
        endpoint = endpoint[len("openapi/v2/"):]
    return {"name_en": requested, "endpoint": endpoint or RUNNINGHUB_DEFAULT_IMAGE_MODELS[0], "output_type": provider_probe.classify_upstream_model(requested), "params": []}


def runninghub_schema_options(field):
    values = []
    for item in (field or {}).get("options") or []:
        if isinstance(item, dict):
            value = item.get("value")
        else:
            value = item
        if value is not None and str(value) != "":
            values.append(str(value))
    return values


def runninghub_schema_value(field, preferred=None):
    preferred = "" if preferred is None else str(preferred).strip()
    options = runninghub_schema_options(field)
    if preferred and (not options or preferred in options):
        return preferred
    default = (field or {}).get("defaultValue")
    if default is not None and str(default) != "":
        return default
    return options[0] if options else preferred


def runninghub_schema_field(params, *keys):
    wanted = {str(k).lower() for k in keys if k}
    for field in params or []:
        if not isinstance(field, dict):
            continue
        names = {str(field.get("fieldKey") or "").lower(), str(field.get("label") or "").lower()}
        if names & wanted:
            return field
    return None


def runninghub_aspect_from_size(size, fallback="1:1"):
    width, height = parse_size_pair(size)
    if width and height:
        divisor = math.gcd(width, height) or 1
        return f"{width // divisor}:{height // divisor}"
    raw = str(size or "").strip().lower()
    if re.fullmatch(r"(auto|\d+\s*:\s*\d+)", raw):
        return raw.replace(" ", "")
    return fallback


def runninghub_resolution_from_size(size, fallback="2k"):
    width, height = parse_size_pair(size)
    if width and height:
        long_edge = max(width, height)
        if long_edge >= 3200:
            return "4k"
        if long_edge >= 1400:
            return "2k"
        return "1k"
    raw = str(size or "").strip().lower()
    return raw if raw in {"1k", "2k", "4k", "480p", "720p", "1080p", "native1080p"} else fallback


def runninghub_size_for_aspect(aspect_ratio, fallback="1280x720"):
    ratio = str(aspect_ratio or "").strip()
    return {
        "9:16": "720x1280",
        "16:9": "1280x720",
        "1:1": "1024x1024",
        "4:3": "1024x768",
        "3:4": "768x1024",
    }.get(ratio, fallback)


def runninghub_apply_schema_defaults(body, params):
    for field in params or []:
        if not isinstance(field, dict):
            continue
        key = str(field.get("fieldKey") or "").strip()
        if not key or key in body:
            continue
        default = field.get("defaultValue")
        options = runninghub_schema_options(field)
        if default is None or default == "":
            if field.get("required") is True and options:
                default = options[0]
            else:
                continue
        ftype = str(field.get("type") or "").upper()
        if ftype == "BOOLEAN":
            body[key] = bool(default) if not isinstance(default, str) else default.lower() == "true"
        elif ftype in {"INT", "INTEGER"}:
            try:
                body[key] = int(default)
            except Exception:
                body[key] = default
        elif ftype == "FLOAT":
            try:
                body[key] = float(default)
            except Exception:
                body[key] = default
        else:
            body[key] = default
    return body


def runninghub_query_status(raw):
    if not isinstance(raw, dict):
        return ""
    values = [
        raw.get("status"),
        raw.get("state"),
        raw.get("taskStatus"),
        raw.get("task_status"),
    ]
    data = raw.get("data")
    if isinstance(data, dict):
        values.extend([data.get("status"), data.get("state"), data.get("taskStatus"), data.get("task_status")])
    for value in values:
        if value is not None:
            return str(value).lower()
    return ""


def runninghub_extract_task_id(raw):
    if not isinstance(raw, dict):
        return ""
    for key in ("taskId", "task_id", "id"):
        if raw.get(key):
            return str(raw[key])
    data = raw.get("data")
    if isinstance(data, dict):
        for key in ("taskId", "task_id", "id"):
            if data.get(key):
                return str(data[key])
    return ""


def runninghub_extract_image(raw):
    if not isinstance(raw, dict):
        raise HTTPException(status_code=502, detail="RunningHub 返回格式不是 JSON 对象")
    containers = [raw]
    data = raw.get("data")
    if isinstance(data, dict):
        containers.append(data)
    for container in containers:
        results = container.get("results") or container.get("result") or container.get("outputs") or container.get("output")
        if isinstance(results, dict):
            results = [results]
        if isinstance(results, list):
            for item in results:
                if isinstance(item, str) and item.startswith(("http://", "https://")):
                    return {"type": "url", "value": item}
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "url" and item.get("value"):
                    return {"type": "url", "value": item["value"]}
                if item.get("type") == "b64" and item.get("value"):
                    return {"type": "b64", "value": item["value"], "mime_type": item.get("mime_type") or "image/png"}
                url = item.get("url") or item.get("fileUrl") or item.get("file_url") or item.get("download_url") or item.get("imageUrl") or item.get("image_url")
                if isinstance(url, list) and url:
                    url = url[0]
                if isinstance(url, str) and url:
                    return {"type": "url", "value": url}
    return online_image.extract_image(raw)


async def runninghub_upload_reference(client, provider, ref):
    path = output_file_from_url(ref.get("url", ""))
    if not path:
        value = ref.get("url", "")
        return value if str(value).startswith(("http://", "https://")) else ""
    upload_url = runninghub_openapi_url(provider, "media/upload/binary")
    headers = {"Authorization": provider_store.bearer_auth_value(runninghub.runninghub_api_key(provider)), "Accept": "application/json"}
    with open(path, "rb") as fh:
        files = {"file": (os.path.basename(path), fh, content_type_for_path(path))}
        response = await client.post(upload_url, headers=headers, files=files, timeout=120)
    response.raise_for_status()
    raw = response.json()
    data = raw.get("data") if isinstance(raw, dict) else None
    candidates = [raw, data] if isinstance(data, dict) else [raw]
    for item in candidates:
        if not isinstance(item, dict):
            continue
        value = item.get("download_url") or item.get("downloadUrl") or item.get("url") or item.get("fileUrl") or item.get("file_url")
        if value:
            return str(value)
    raise HTTPException(status_code=502, detail=f"RunningHub 上传图片未返回 download_url：{raw}")


async def wait_for_runninghub_image_task(client, provider, task_id):
    query_url = runninghub_openapi_url(provider, "query")
    deadline = time.monotonic() + 1800
    last_payload = None
    while time.monotonic() < deadline:
        await asyncio.sleep(2)
        response = await client.post(query_url, headers=runninghub_api_headers(provider), json={"taskId": task_id})
        response.raise_for_status()
        raw = response.json()
        last_payload = raw
        status = runninghub_query_status(raw)
        if status in {"success", "succeeded", "completed", "complete", "finished", "finish", "done", "3"}:
            return raw
        if status in {"failed", "fail", "error", "canceled", "cancelled", "4"}:
            raise HTTPException(status_code=502, detail=f"RunningHub 任务失败：{raw}")
        try:
            return {"data": {"results": [runninghub_extract_image(raw)]}}
        except HTTPException:
            pass
    raise HTTPException(status_code=504, detail=f"RunningHub 生图任务超时：{last_payload}")


async def wait_for_runninghub_openapi_task(client, provider, task_id, output_kind=""):
    query_url = runninghub_openapi_url(provider, "query")
    deadline = time.monotonic() + 1800
    last_payload = None
    while time.monotonic() < deadline:
        await asyncio.sleep(3)
        response = await client.post(query_url, headers=runninghub_json_headers(provider), json={"taskId": task_id})
        response.raise_for_status()
        raw = response.json()
        last_payload = raw
        status = runninghub_query_status(raw).upper()
        if status in {"SUCCESS", "SUCCEEDED", "COMPLETED", "COMPLETE", "FINISHED", "DONE", "3"}:
            return raw
        if status in {"FAILED", "FAIL", "ERROR", "CANCEL", "CANCELED", "CANCELLED", "4"}:
            raise HTTPException(status_code=502, detail=f"RunningHub 任务失败：{runninghub.runninghub_fail_reason(raw) or raw}")
        if output_kind == "video" and video_output_urls(raw):
            return raw
    raise HTTPException(status_code=504, detail=f"RunningHub 任务超时：{last_payload or task_id}")


def runninghub_entry_config_from_model(provider, model):
    """解析 model=app:ID / workflow:ID，返回 {kind,id,fields,optionalImageMode,workflowJson} 或 None。"""
    text = str(model or "").strip()
    match = RUNNINGHUB_ENTRY_MODEL_RE.match(text)
    if not match:
        return None
    kind = match.group(1)
    entry_id = match.group(2).strip()
    if not entry_id:
        return None
    if kind == "workflow":
        key = runninghub_workflow_store_key(entry_id)
        with RUNNINGHUB_WORKFLOW_LOCK:
            store = load_runninghub_workflow_store()
        cfg = runninghub_select_workflow_config(store.get(key), runninghub_provider_workflow_config(key), key)
        if not isinstance(cfg, dict):
            # 退回到 provider 列表中的内联条目
            entry = next(
                (e for e in (provider.get("rh_workflows") or []) if runninghub_entry_id(e, "workflow") == entry_id),
                None,
            )
            if not entry:
                return None
            cfg = {
                "fields": entry.get("fields") or [],
                "optionalImageMode": entry.get("optionalImageMode") or "prune-workflow",
                "workflowJson": entry.get("workflowJson") if isinstance(entry.get("workflowJson"), dict) else {},
            }
        return {
            "kind": "workflow",
            "id": entry_id,
            "fields": cfg.get("fields") or [],
            "optionalImageMode": cfg.get("optionalImageMode") or "prune-workflow",
            "workflowJson": cfg.get("workflowJson") if isinstance(cfg.get("workflowJson"), dict) else {},
        }
    entry = next(
        (e for e in (provider.get("rh_apps") or []) if runninghub_entry_id(e, "app") == entry_id),
        None,
    )
    if not entry:
        return None
    return {
        "kind": "app",
        "id": entry_id,
        "fields": entry.get("fields") or [],
        "optionalImageMode": "",
        "workflowJson": {},
    }


async def generate_runninghub_entry_image(prompt, size, model, reference_images, provider, entry):
    """运行 RunningHub 工作流 / AI 应用（与智能画布一致的运行方式），返回首张图片结果。"""
    kind = entry["kind"]
    entry_id = entry["id"]
    fields = rh_sort_fields([f for f in (entry.get("fields") or []) if isinstance(f, dict) and f.get("enabled") is True])
    idx_map = rh_field_indexes(fields)
    use_wallet = False
    timeout = httpx.Timeout(connect=20.0, read=1800.0, write=240.0, pool=20.0)
    aspect = runninghub_aspect_from_size(size, "")
    resolution = runninghub_resolution_from_size(size, "")
    width, height = parse_size_pair(size)
    def requested_size_field_value(field):
        names = {
            str(field.get("fieldName") or "").strip().lower(),
            str(field.get("fieldKey") or "").strip().lower(),
            str(field.get("label") or "").strip().lower(),
        }
        if aspect and names & {"aspectratio", "aspect_ratio", "ratio"}:
            return runninghub_schema_value(field, aspect)
        if resolution and "resolution" in names:
            return runninghub_schema_value(field, resolution)
        if width and "width" in names:
            return width
        if height and "height" in names:
            return height
        return None
    async with httpx.AsyncClient(timeout=timeout) as client:
        uploaded = []
        for ref in (reference_images or [])[:ONLINE_IMAGE_REFERENCE_MAX]:
            ref_url = ref.get("url") if isinstance(ref, dict) else ref
            if not ref_url:
                continue
            file_name = await runninghub_upload_local_to_filename(client, provider, ref_url, use_wallet)
            if file_name:
                uploaded.append(file_name)

        node_info_list = []
        prompt_text = str(prompt or "").strip()
        for field in fields:
            node_id = str(field.get("nodeId") or "").strip()
            field_name = str(field.get("fieldName") or "").strip()
            if not node_id or not field_name:
                continue
            kind_f = rh_field_kind(field)
            if kind_f in ("image", "video", "audio"):
                if kind_f != "image":
                    continue  # 在线生图仅提供图片素材
                index = idx_map.get((node_id, field_name), 0)
                value = uploaded[index] if index < len(uploaded) else ""
                if not value:
                    # 工作流可选图（required!=True）无输入则跳过；必填图回退默认值
                    if field.get("required") is True:
                        value = rh_default_value(field)
                        if not value:
                            continue
                    else:
                        continue
                node_info_list.append({"nodeId": node_id, "fieldName": field_name, "fieldValue": value})
            elif rh_field_role(field) == "prompt":
                value = prompt_text or rh_default_value(field)
                node_info_list.append({"nodeId": node_id, "fieldName": field_name, "fieldValue": value})
            elif kind_f == "number" and field.get("random_enabled") is True:
                node_info_list.append({"nodeId": node_id, "fieldName": field_name, "fieldValue": rh_random_field_value(field)})
            else:
                value = requested_size_field_value(field)
                if value is None:
                    value = rh_default_value(field)
                node_info_list.append({"nodeId": node_id, "fieldName": field_name, "fieldValue": value})

        api_key = runninghub.runninghub_api_key(provider, use_wallet=use_wallet)
        if kind == "workflow":
            submit_url = runninghub.runninghub_endpoint_url(provider, "/task/openapi/create")
            body = {"apiKey": api_key, "workflowId": entry_id, "addMetadata": True}
            if node_info_list:
                body["nodeInfoList"] = node_info_list
        else:
            submit_url = runninghub.runninghub_endpoint_url(provider, "/task/openapi/ai-app/run")
            body = {"apiKey": api_key, "webappId": entry_id, "nodeInfoList": node_info_list}

        response = await client.post(submit_url, headers=runninghub_app_headers(True, use_wallet), json=body)
        raw = response.json()
        if not (isinstance(raw, dict) and raw.get("code") in (0, "0")):
            raise HTTPException(status_code=502, detail=(raw.get("msg") if isinstance(raw, dict) else "") or f"RunningHub 提交失败：{raw}")
        task_id = raw.get("data", {}).get("taskId") if isinstance(raw.get("data"), dict) else ""
        if not task_id:
            raise HTTPException(status_code=502, detail=f"RunningHub 未返回 taskId：{raw}")

        query_url = runninghub.runninghub_endpoint_url(provider, "/task/openapi/outputs")
        deadline = time.monotonic() + 1800
        last_payload = None
        while time.monotonic() < deadline:
            await asyncio.sleep(2.5)
            query_response = await client.post(query_url, headers=runninghub_app_headers(True), json={"apiKey": api_key, "taskId": task_id})
            query_raw = query_response.json()
            last_payload = query_raw
            code = query_raw.get("code") if isinstance(query_raw, dict) else None
            if code in (0, "0"):
                outputs = runninghub.runninghub_extract_outputs(query_raw.get("data"))
                for remote in outputs:
                    if str(remote or "").startswith(("http://", "https://", "/output/", "/assets/")):
                        return {"type": "url", "value": str(remote)}, query_raw
                raise HTTPException(status_code=502, detail=f"RunningHub 任务无图片输出：{query_raw}")
            if code in (805, "805"):
                raise HTTPException(status_code=502, detail=f"RunningHub 任务失败：{runninghub.runninghub_fail_reason(query_raw) or query_raw}")
            # 804 运行中 / 813 排队中 / 其他状态继续轮询
        raise HTTPException(status_code=504, detail=f"RunningHub 任务超时：{last_payload}")


async def generate_runninghub_provider_image(prompt, size, model, reference_images=None, provider=None):
    entry = runninghub_entry_config_from_model(provider, model)
    if entry:
        return await generate_runninghub_entry_image(prompt, size, model, reference_images, provider, entry)
    model_def = await runninghub_model_definition(provider, model)
    endpoint = runninghub_task_endpoint(provider, model_def.get("endpoint") or model)
    params = model_def.get("params") if isinstance(model_def.get("params"), list) else []
    aspect = runninghub_aspect_from_size(size, "1:1")
    resolution = runninghub_resolution_from_size(size, "2k")
    body = {"prompt": prompt}
    if runninghub_schema_field(params, "aspectRatio"):
        field = runninghub_schema_field(params, "aspectRatio")
        body["aspectRatio"] = runninghub_schema_value(field, aspect)
    elif runninghub_schema_field(params, "ratio"):
        field = runninghub_schema_field(params, "ratio")
        body["ratio"] = runninghub_schema_value(field, aspect)
    if runninghub_schema_field(params, "resolution"):
        field = runninghub_schema_field(params, "resolution")
        body["resolution"] = runninghub_schema_value(field, resolution)
    width, height = parse_size_pair(size)
    if width and height:
        if runninghub_schema_field(params, "width"):
            body["width"] = width
        if runninghub_schema_field(params, "height"):
            body["height"] = height
    quality_field = runninghub_schema_field(params, "quality")
    if quality_field:
        body["quality"] = runninghub_schema_value(quality_field, "medium")
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=20.0, read=1800.0, write=180.0, pool=20.0)) as client:
        image_urls = []
        for ref in (reference_images or [])[:ONLINE_IMAGE_REFERENCE_MAX]:
            url = await runninghub_upload_reference(client, provider, ref)
            if url:
                image_urls.append(url)
        if image_urls:
            image_field = runninghub_schema_field(params, "imageUrls", "imageUrl", "images", "image")
            key = str((image_field or {}).get("fieldKey") or "imageUrls")
            if key.endswith("s") or (image_field or {}).get("multipleInputs") is True:
                body[key] = image_urls
            else:
                body[key] = image_urls[0]
        runninghub_apply_schema_defaults(body, params)
        response = await client.post(endpoint, headers=runninghub_json_headers(provider), json=body)
        response.raise_for_status()
        raw = response.json()
        try:
            return runninghub_extract_image(raw), raw
        except HTTPException:
            task_id = runninghub_extract_task_id(raw)
            if not task_id:
                raise HTTPException(status_code=502, detail=f"RunningHub 未返回 taskId 或图片结果：{raw}")
        result = await wait_for_runninghub_image_task(client, provider, task_id)
        return runninghub_extract_image(result), result


async def generate_runninghub_video(payload, provider):
    model_def = await runninghub_model_definition(provider, payload.model)
    endpoint = runninghub_task_endpoint(provider, model_def.get("endpoint") or payload.model)
    params = model_def.get("params") if isinstance(model_def.get("params"), list) else []
    body = {"prompt": str(payload.prompt or "")}
    aspect = str(payload.aspect_ratio or "16:9").strip() or "16:9"
    if runninghub_schema_field(params, "aspectRatio"):
        field = runninghub_schema_field(params, "aspectRatio")
        body["aspectRatio"] = runninghub_schema_value(field, aspect)
    if runninghub_schema_field(params, "ratio"):
        field = runninghub_schema_field(params, "ratio")
        body["ratio"] = runninghub_schema_value(field, aspect)
    if runninghub_schema_field(params, "size"):
        field = runninghub_schema_field(params, "size")
        body["size"] = runninghub_schema_value(field, runninghub_size_for_aspect(aspect))
    if runninghub_schema_field(params, "duration"):
        field = runninghub_schema_field(params, "duration")
        body["duration"] = runninghub_schema_value(field, str(max(1, min(60, int(payload.duration or 5)))))
    if runninghub_schema_field(params, "resolution"):
        field = runninghub_schema_field(params, "resolution")
        body["resolution"] = runninghub_schema_value(field, str(payload.resolution or "720p").lower())
    if runninghub_schema_field(params, "generateAudio"):
        body["generateAudio"] = bool(payload.generate_audio)
    if runninghub_schema_field(params, "watermark"):
        body["watermark"] = bool(payload.watermark)
    async with httpx.AsyncClient(timeout=VIDEO_POLL_TIMEOUT) as client:
        image_urls = []
        for ref in (payload.images or [])[:10]:
            ref_url = getattr(ref, "url", "") or ""
            if ref_url:
                up = await runninghub_upload_reference(client, provider, {"url": ref_url})
                if up:
                    image_urls.append(up)
        if image_urls:
            image_field = runninghub_schema_field(params, "imageUrls", "imageUrl", "firstFrameImage", "lastFrameImage", "referenceImages")
            key = str((image_field or {}).get("fieldKey") or "imageUrls")
            if key in {"firstFrameImage", "first_frame_image"}:
                body[key] = image_urls[0]
                last_field = runninghub_schema_field(params, "lastFrameImage", "last_frame_image")
                if len(image_urls) > 1 and last_field:
                    body[str(last_field.get("fieldKey"))] = image_urls[1]
            elif key.endswith("s") or (image_field or {}).get("multipleInputs") is True:
                body[key] = image_urls
            else:
                body[key] = image_urls[0]
        runninghub_apply_schema_defaults(body, params)
        response = await client.post(endpoint, headers=runninghub_json_headers(provider), json=body)
        response.raise_for_status()
        raw = response.json()
        task_id = runninghub_extract_task_id(raw)
        result = raw
        if task_id and not video_output_urls(raw):
            result = await wait_for_runninghub_openapi_task(client, provider, task_id, "video")
        urls = video_output_urls(result)
        if not urls:
            outputs = runninghub.runninghub_extract_outputs(result.get("data") if isinstance(result, dict) else result)
            urls = [url for url in outputs if str(url).startswith(("http://", "https://", "/output/", "/assets/"))]
        if not urls:
            raise HTTPException(status_code=502, detail=f"RunningHub 视频生成成功但没有返回视频：{result}")
        local_urls = [await save_remote_video_to_output(url, prefix="rh_video_") for url in urls]
        return {"videos": local_urls, "task_id": task_id, "raw": result}
