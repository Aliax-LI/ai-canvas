"""Online image generation, task query, and canvas async tasks — legacy parity."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import time
import urllib.parse
import uuid
from typing import Any

import httpx
from fastapi import HTTPException
from PIL import Image

from infinite_canvas.core.media import content_type_for_path, output_path_for, output_url_for
from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.provider_constants import SUPPORTED_IMAGE_REQUEST_MODES
from infinite_canvas.core.runtime_config import AI_BASE_URL, IMAGE_MODEL
from infinite_canvas.core.websocket import GLOBAL_LOOP, manager
from infinite_canvas.schemas.online_image import ImageTaskQueryRequest, OnlineImageRequest
from infinite_canvas.services import asset_ai, history as history_service, provider_store
from infinite_canvas.services.comfyui_generate import (
    CANVAS_TASK_LOCK,
    CANVAS_TASKS,
    is_gpt_image_2_model,
    is_runninghub_provider,
)
from infinite_canvas.services.jimeng import JimengPendingError, jimeng_pending_payload
from infinite_canvas.services.provider_store import is_jimeng_provider

ONLINE_IMAGE_REFERENCE_MAX = int(os.getenv("ONLINE_IMAGE_REFERENCE_MAX", "20"))
IMAGE_TASK_TIMEOUT = float(os.getenv("IMAGE_TASK_TIMEOUT", "600"))
IMAGE_POLL_INTERVAL = float(os.getenv("IMAGE_POLL_INTERVAL", "3"))
APIMART_IMAGE_TASK_TIMEOUT = float(os.getenv("APIMART_IMAGE_TASK_TIMEOUT", "1800"))
APIMART_IMAGE_POLL_INTERVAL = float(os.getenv("APIMART_IMAGE_POLL_INTERVAL", "5"))
APIMART_IMAGE_INITIAL_POLL_DELAY = float(os.getenv("APIMART_IMAGE_INITIAL_POLL_DELAY", "3"))

IMAGE_OUTPUT_KEY_HINTS = (
    "url",
    "image_url",
    "imageUrl",
    "image",
    "output_url",
    "outputUrl",
    "result_url",
    "resultUrl",
    "download_url",
    "downloadUrl",
    "asset_url",
    "assetUrl",
)
IMAGE_CONTAINER_KEY_HINTS = (
    "images",
    "image",
    "output",
    "outputs",
    "result",
    "results",
    "data",
    "items",
    "files",
)
IMAGE_BASE64_KEY_HINTS = ("b64_json", "base64", "image_base64", "imageBase64")
IMAGE_TASK_SUCCESS_STATUSES = {
    "SUCCESS",
    "SUCCESSFUL",
    "SUCCEED",
    "SUCCEEDED",
    "COMPLETED",
    "COMPLETE",
    "DONE",
    "FINISHED",
    "OK",
    "READY",
}
IMAGE_TASK_FAILED_STATUSES = {
    "FAILURE",
    "FAILED",
    "FAIL",
    "ERROR",
    "ERRORED",
    "CANCELED",
    "CANCELLED",
    "TIMEOUT",
    "REJECTED",
    "EXPIRED",
}


def looks_like_generated_image_url(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith("data:image/"):
        return True
    clean = text.split("?", 1)[0].split("#", 1)[0].lower()
    return text.startswith(("http://", "https://", "/output/", "/assets/")) and re.search(
        r"\.(png|jpe?g|webp|gif|bmp|tiff?)$", clean
    )


def extract_image_flexible(value: object, depth: int = 0) -> dict[str, Any] | None:
    if depth > 8 or value is None:
        return None
    if isinstance(value, str):
        return {"type": "url", "value": value} if looks_like_generated_image_url(value) else None
    if isinstance(value, list):
        for item in value:
            found = extract_image_flexible(item, depth + 1)
            if found:
                return found
        return None
    if not isinstance(value, dict):
        return None
    for key in IMAGE_BASE64_KEY_HINTS:
        item = value.get(key)
        if isinstance(item, str) and item.strip():
            return {
                "type": "b64",
                "value": item.strip(),
                "mime_type": value.get("mime_type") or value.get("mimeType") or "image/png",
            }
    for key in IMAGE_OUTPUT_KEY_HINTS:
        item = value.get(key)
        if isinstance(item, str) and looks_like_generated_image_url(item):
            return {"type": "url", "value": item}
        found = extract_image_flexible(item, depth + 1)
        if found:
            return found
    for key in IMAGE_CONTAINER_KEY_HINTS:
        found = extract_image_flexible(value.get(key), depth + 1)
        if found:
            return found
    return None


def extract_images(data: object) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add_image(item: dict[str, Any]) -> None:
        img_type = item.get("type") or "url"
        value = item.get("value")
        if not value:
            return
        key = (img_type, value)
        if key in seen:
            return
        seen.add(key)
        found.append(item)

    def collect(value: object, depth: int = 0) -> None:
        if depth > 8 or value is None:
            return
        if isinstance(value, str):
            if looks_like_generated_image_url(value):
                add_image({"type": "url", "value": value})
            return
        if isinstance(value, list):
            for item in value:
                collect(item, depth + 1)
            return
        if not isinstance(value, dict):
            return
        for key in IMAGE_BASE64_KEY_HINTS:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                add_image(
                    {
                        "type": "b64",
                        "value": item.strip(),
                        "mime_type": value.get("mime_type") or value.get("mimeType") or "image/png",
                    }
                )
        for key in IMAGE_OUTPUT_KEY_HINTS:
            item = value.get(key)
            if isinstance(item, str) and looks_like_generated_image_url(item):
                add_image({"type": "url", "value": item})
            else:
                collect(item, depth + 1)
        for key in IMAGE_CONTAINER_KEY_HINTS:
            collect(value.get(key), depth + 1)

    if isinstance(data, dict):
        candidates = data.get("candidates")
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                content = candidate.get("content") or {}
                parts = content.get("parts") if isinstance(content, dict) else None
                if not isinstance(parts, list):
                    continue
                for part in parts:
                    if not isinstance(part, dict):
                        continue
                    inline = part.get("inlineData") or part.get("inline_data") or {}
                    if not isinstance(inline, dict):
                        continue
                    value = inline.get("data")
                    if value:
                        add_image(
                            {
                                "type": "b64",
                                "value": value,
                                "mime_type": inline.get("mimeType") or inline.get("mime_type") or "image/png",
                            }
                        )
        current: object = data
        if (
            isinstance(current, dict)
            and isinstance(current.get("data"), dict)
            and isinstance(current["data"].get("result"), dict)
        ):
            current = current["data"]
        if isinstance(current, dict) and isinstance(current.get("result"), dict):
            for item in current["result"].get("images") or []:
                if not isinstance(item, dict):
                    collect(item)
                    continue
                url = item.get("url")
                if isinstance(url, list):
                    for one in url:
                        collect(one)
                else:
                    collect(url)
                collect(item)
        collect(data)
        if isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), dict):
            collect(data["data"]["data"])
    if found:
        return found
    raise HTTPException(status_code=502, detail="无法识别生图接口返回格式")


def extract_image(data: object) -> dict[str, Any]:
    try:
        images = extract_images(data)
        if images:
            return images[0]
    except HTTPException:
        pass
    if isinstance(data, dict):
        flexible = extract_image_flexible(data)
        if flexible:
            return flexible
        images = data.get("data") or []
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict) and first.get("url"):
                return {"type": "url", "value": first["url"]}
            if isinstance(first, dict) and first.get("b64_json"):
                return {"type": "b64", "value": first["b64_json"]}
    raise HTTPException(status_code=502, detail="无法识别生图接口返回格式")


def extract_task_id(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    if data.get("task_id"):
        return str(data["task_id"])
    if data.get("id") and str(data.get("id", "")).startswith("task"):
        return str(data["id"])
    nested = data.get("data")
    if isinstance(nested, list) and nested and isinstance(nested[0], dict):
        return extract_task_id(nested[0])
    if isinstance(nested, dict):
        return extract_task_id(nested)
    return None


def extract_task_id_from_text(text: str) -> str:
    value = str(text or "")
    match = re.search(r"(?:task_id|taskId|task id)\s*[=:：]\s*([A-Za-z0-9_.:-]+)", value, re.IGNORECASE)
    return match.group(1) if match else ""


def images_api_unsupported(response: httpx.Response) -> bool:
    text = str(response.text or "").lower()
    return "images api is not supported" in text or "not supported for this platform" in text


def normalize_image_request_mode(value: str) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in SUPPORTED_IMAGE_REQUEST_MODES else "openai"


def detect_image_request_mode(base_url: str = "", models: list[str] | None = None) -> str:
    base = str(base_url or "").strip().lower()
    if "apihub.agnes-ai.com" in base:
        return "openai-json"
    for model in models or []:
        if str(model or "").strip().lower().startswith("agnes-image-"):
            return "openai-json"
    return ""


def effective_image_request_mode(provider: dict[str, Any], model: str = "") -> str:
    detected = detect_image_request_mode(str(provider.get("base_url") or ""), [model])
    if detected:
        return detected
    return normalize_image_request_mode(str(provider.get("image_request_mode") or ""))


def provider_endpoint_url(provider: dict[str, Any], key: str, default_path: str) -> str:
    base_url = str(provider.get("base_url") or AI_BASE_URL).strip().rstrip("/")
    override = str(provider.get(key) or "").strip()
    if override:
        if re.match(r"^https?://", override, re.I):
            return override.rstrip("/")
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}{override}"
        return override
    for prefix in ("/api/v3", "/v1beta", "/v1", "/v2"):
        if base_url.endswith(prefix) and default_path.startswith(f"{prefix}/"):
            return f"{base_url}{default_path[len(prefix):]}"
    return f"{base_url}{default_path}"


def is_image_reference(ref: dict[str, Any]) -> bool:
    kind = str(ref.get("kind") or "").strip().lower()
    mime = str(ref.get("mime") or "").strip().lower()
    url = str(ref.get("url") or "").strip().lower()
    if kind:
        return kind == "image"
    if mime:
        return mime.startswith("image/")
    return bool(re.search(r"\.(png|jpe?g|webp|gif|bmp|tiff?)(\?|#|$)", url))


def image_references(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [ref for ref in (refs or []) if is_image_reference(ref)]


def image_task_url_for_provider(provider: dict[str, Any], task_id: str) -> str:
    base_url = str(provider.get("base_url") or AI_BASE_URL).rstrip("/")
    is_apimart = asset_ai.is_apimart_provider(provider)
    if is_apimart:
        return f"{base_url}/tasks/{task_id}" if base_url.endswith("/v1") else f"{base_url}/v1/tasks/{task_id}"
    return f"{base_url}/images/tasks/{task_id}" if base_url.endswith("/v1") else f"{base_url}/v1/images/tasks/{task_id}"


def image_task_data(payload: object) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else {}


def image_task_status(payload: object) -> str:
    task_data = image_task_data(payload)
    return str(task_data.get("status") or task_data.get("task_status") or "").upper()


def image_task_fail_reason(payload: object) -> str:
    task_data = image_task_data(payload)
    error = task_data.get("error") if isinstance(task_data.get("error"), dict) else {}
    if isinstance(payload, dict):
        return (
            task_data.get("fail_reason")
            or task_data.get("message")
            or error.get("message")
            or payload.get("message")
            or "生图任务失败"
        )
    return "生图任务失败"


async def fetch_image_task_payload(
    client: httpx.AsyncClient, task_id: str, provider: dict[str, Any] | None = None
) -> dict[str, Any]:
    task_url = image_task_url_for_provider(provider or {}, task_id)
    response = await client.get(task_url, headers=asset_ai.api_headers(provider=provider))
    response.raise_for_status()
    return response.json()


async def wait_for_image_task(
    client: httpx.AsyncClient, task_id: str, provider: dict[str, Any] | None = None
) -> dict[str, Any]:
    is_apimart = asset_ai.is_apimart_provider(provider)
    timeout = APIMART_IMAGE_TASK_TIMEOUT if is_apimart else IMAGE_TASK_TIMEOUT
    interval = APIMART_IMAGE_POLL_INTERVAL if is_apimart else IMAGE_POLL_INTERVAL
    initial_delay = APIMART_IMAGE_INITIAL_POLL_DELAY if is_apimart else 0
    deadline = time.monotonic() + timeout
    last_payload: dict[str, Any] = {}
    while time.monotonic() < deadline:
        if initial_delay:
            await asyncio.sleep(min(initial_delay, max(0.0, deadline - time.monotonic())))
            initial_delay = 0
            if time.monotonic() >= deadline:
                break
        last_payload = await fetch_image_task_payload(client, task_id, provider)
        status = image_task_status(last_payload)
        if not status:
            try:
                if extract_image(last_payload):
                    return last_payload
            except HTTPException:
                pass
        if status in IMAGE_TASK_SUCCESS_STATUSES:
            return last_payload
        if status in IMAGE_TASK_FAILED_STATUSES:
            raise HTTPException(status_code=502, detail=f"生图任务失败：{image_task_fail_reason(last_payload)}")
        await asyncio.sleep(min(interval, max(0.0, deadline - time.monotonic())))
    raw_text = json.dumps(last_payload, ensure_ascii=False)[:800] if last_payload else ""
    extra = f"，最后响应：{raw_text}" if raw_text else ""
    raise HTTPException(status_code=504, detail=f"生图任务超时（已等待 {int(timeout)} 秒），task_id={task_id}{extra}")


async def save_ai_image_to_output(image_data: dict[str, Any], prefix: str = "online_", category: str = "output") -> str:
    filename = f"{prefix}{uuid.uuid4().hex[:10]}.png"
    path = output_path_for(filename, category)
    path.parent.mkdir(parents=True, exist_ok=True)
    if image_data["type"] == "b64":
        mime_type = str(image_data.get("mime_type") or "").lower()
        if "jpeg" in mime_type or "jpg" in mime_type:
            filename = filename[:-4] + ".jpg"
            path = output_path_for(filename, category)
        elif "webp" in mime_type:
            filename = filename[:-4] + ".webp"
            path = output_path_for(filename, category)
        path.write_bytes(base64.b64decode(image_data["value"]))
        return output_url_for(filename, category)
    value = image_data["value"]
    if value.startswith("/output/") or value.startswith("/assets/"):
        return value
    try:
        timeout = httpx.Timeout(connect=20.0, read=300.0, write=60.0, pool=20.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(value)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                filename = filename[:-4] + ".jpg"
                path = output_path_for(filename, category)
            elif "webp" in content_type:
                filename = filename[:-4] + ".webp"
                path = output_path_for(filename, category)
            path.write_bytes(response.content)
            return output_url_for(filename, category)
    except Exception as exc:
        print(f"保存上游图片失败: {exc}")
        return value


def image_output_meta(url: str, source_item: dict[str, Any] | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {"url": url, "kind": "image"}
    if not url:
        return meta
    parsed_name = os.path.basename(urllib.parse.urlparse(str(url)).path)
    if parsed_name:
        meta["name"] = parsed_name
    if isinstance(source_item, dict):
        for key in ("natural_w", "natural_h", "width", "height", "w", "h", "layout_w", "layout_h"):
            try:
                value = int(float(source_item.get(key) or 0))
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                meta[key] = value
    path = output_file_from_url(url)
    if path and path.exists():
        try:
            with Image.open(path) as img:
                width, height = img.size
            if width > 0 and height > 0:
                meta.update({"natural_w": width, "natural_h": height, "width": width, "height": height})
        except Exception:
            pass
    return meta


async def generate_ai_image(
    prompt: str,
    size: str,
    quality: str,
    model: str,
    reference_images: list[dict[str, Any]] | None = None,
    provider_id: str = "comfly",
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider = provider_store.get_api_provider(provider_id)
    if provider["id"] == "modelscope":
        from infinite_canvas.services.provider_image import generate_modelscope_provider_image

        return await generate_modelscope_provider_image(prompt, size, model, reference_images, provider)
    if is_jimeng_provider(provider):
        from infinite_canvas.services.jimeng_generate import generate_jimeng_provider_image

        return await generate_jimeng_provider_image(prompt, size, model, reference_images, provider)
    if is_runninghub_provider(provider):
        from infinite_canvas.services.runninghub_provider import generate_runninghub_provider_image

        return await generate_runninghub_provider_image(prompt, size, model, reference_images, provider)
    if asset_ai.effective_protocol(provider, model) == "gemini":
        from infinite_canvas.services.provider_image import generate_gemini_provider_image

        return await generate_gemini_provider_image(prompt, size, model, reference_images, provider)
    if asset_ai.is_volcengine_provider(provider):
        from infinite_canvas.services.provider_image import generate_volcengine_provider_image

        return await generate_volcengine_provider_image(prompt, size, model, reference_images, provider)

    is_gpt2 = is_gpt_image_2_model(model)
    is_apimart = asset_ai.is_apimart_provider(provider)
    quality = str(quality or "").strip().lower()
    if quality not in {"low", "medium", "high"}:
        quality = ""
    base_url = str(provider.get("base_url") or AI_BASE_URL).rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider['id']} 未配置 Base URL")
    gen_url = provider_endpoint_url(provider, "image_generation_endpoint", "/v1/images/generations")
    edit_url = provider_endpoint_url(provider, "image_edit_endpoint", "/v1/images/edits")
    refs = [ref for ref in (reference_images or []) if ref.get("url")]
    image_refs = image_references(refs)
    image_request_mode = effective_image_request_mode(provider, model)
    request_timeout = (
        httpx.Timeout(connect=20.0, read=1800.0, write=120.0, pool=20.0)
        if (is_gpt2 or is_apimart or image_request_mode == "openai-json")
        else httpx.Timeout(connect=20.0, read=1800.0, write=120.0, pool=20.0)
    )
    async with httpx.AsyncClient(timeout=request_timeout) as client:
        response: httpx.Response | None = None

        async def post_openai_edits(edit_files: list[tuple[str, tuple[str, object, str]]] | None = None) -> httpx.Response:
            data = {"model": model, "prompt": prompt, "size": size}
            if quality:
                data["quality"] = quality
            return await client.post(
                edit_url,
                headers=asset_ai.api_headers(json_body=False, provider=provider, model=model),
                data=data,
                files=edit_files if edit_files is not None else [],
            )

        if image_request_mode == "openai-json":
            extra_body = {"response_format": "url"}
            body = {"model": model, "prompt": prompt, "size": size, "extra_body": extra_body}
            response = await client.post(gen_url, headers=asset_ai.api_headers(provider=provider, model=model), json=body)
        elif is_gpt2 and not image_refs:
            body = {"model": model, "prompt": prompt, "size": size}
            if quality:
                body["quality"] = quality
            response = await client.post(gen_url, headers=asset_ai.api_headers(provider=provider, model=model), json=body)
            if response.status_code >= 400 and images_api_unsupported(response):
                response = await post_openai_edits()
        elif image_refs:
            files: list[tuple[str, tuple[str, object, str]]] = []
            opened: list[object] = []
            edit_failed_text = ""
            try:
                for ref in image_refs[:ONLINE_IMAGE_REFERENCE_MAX]:
                    path = output_file_from_url(ref.get("url", ""))
                    if not path:
                        continue
                    fh = open(path, "rb")
                    opened.append(fh)
                    files.append(("image", (path.name, fh, content_type_for_path(path))))
                try:
                    response = await post_openai_edits(files)
                    if response.status_code >= 400:
                        edit_failed_text = response.text[:500]
                        response = None
                except httpx.HTTPError as exc:
                    edit_failed_text = str(exc)
                    response = None
            finally:
                for fh in opened:
                    fh.close()
            if response is None:
                if is_gpt2:
                    raise HTTPException(
                        status_code=502,
                        detail=f"GPT-Image-2 编辑接口 /images/edits 调用失败：{edit_failed_text[:300]}",
                    )
                body = {
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "response_format": "url",
                    "n": 1,
                }
                if quality:
                    body["quality"] = quality
                response = await client.post(gen_url, headers=asset_ai.api_headers(provider=provider, model=model), json=body)
        else:
            body = {"model": model, "prompt": prompt, "size": size, "response_format": "url", "n": 1}
            if quality:
                body["quality"] = quality
            response = await client.post(gen_url, headers=asset_ai.api_headers(provider=provider, model=model), json=body)
            if response.status_code >= 400 and images_api_unsupported(response):
                response = await post_openai_edits()
        if response is None:
            raise HTTPException(status_code=502, detail="上游生图接口无响应")
        response.raise_for_status()
        raw = response.json()
        try:
            return extract_image(raw), raw
        except HTTPException:
            task_id = extract_task_id(raw)
            if not task_id:
                raise
        try:
            task_result = await wait_for_image_task(client, task_id, provider)
            return extract_image(task_result), task_result
        except HTTPException as exc:
            exc.upstream_task_id = task_id  # type: ignore[attr-defined]
            raise


async def build_online_image_result(payload: OnlineImageRequest) -> dict[str, Any]:
    provider = provider_store.get_api_provider(payload.provider_id)
    default_model = (provider.get("image_models") or [IMAGE_MODEL])[0]
    model = asset_ai.selected_model(payload.model, default_model)
    refs = [ref.model_dump() for ref in payload.reference_images if ref.url]
    image_refs = image_references(refs)
    count = max(1, min(8, int(payload.n or 1)))

    async def generate_one() -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
        image_data, raw_item = await generate_ai_image(
            payload.prompt, payload.size, payload.quality, model, image_refs, provider["id"]
        )
        try:
            image_items = extract_images(raw_item) if isinstance(raw_item, dict) else [image_data]
        except HTTPException:
            image_items = [image_data]
        local_urls: list[str] = []
        local_items: list[dict[str, Any]] = []
        for item in image_items:
            local_url = await save_ai_image_to_output(item, prefix="online_")
            if local_url:
                local_urls.append(local_url)
                local_items.append(image_output_meta(local_url, item))
        return local_urls, local_items, raw_item if isinstance(raw_item, dict) else {}

    try:
        generated = await asyncio.gather(*(generate_one() for _ in range(count)))
    except httpx.HTTPStatusError as exc:
        text = exc.response.text or ""
        raise HTTPException(status_code=exc.response.status_code, detail=f"上游生图接口错误：{text[:300]}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"请求上游生图接口失败：{exc}") from exc

    local_urls = [url for urls, _items, _raw in generated for url in (urls or []) if url]
    local_items = [item for _urls, items, _raw in generated for item in (items or []) if item.get("url")]
    raw = generated[0][2] if generated else {}
    if not local_urls:
        provider_name = provider.get("name") or provider["id"]
        raw_text = json.dumps(raw, ensure_ascii=False)[:800] if isinstance(raw, (dict, list)) else str(raw)[:800]
        raise HTTPException(status_code=502, detail=f"{provider_name} 没有返回图片：{raw_text}")
    result = {
        "prompt": payload.prompt,
        "images": local_urls,
        "image_items": local_items,
        "timestamp": time.time(),
        "type": "online",
        "model": model,
        "provider_id": provider["id"],
        "provider_name": provider.get("name") or provider["id"],
        "task_id": extract_task_id(raw) if isinstance(raw, dict) else None,
        "request_id": raw.get("id") if isinstance(raw, dict) else None,
        "params": {
            "provider_id": provider["id"],
            "model": model,
            "size": payload.size,
            "quality": payload.quality,
            "n": count,
            "reference_images": refs,
        },
        "raw_usage": raw.get("usage") if isinstance(raw, dict) else None,
    }
    history_service.save_to_history(result)
    if GLOBAL_LOOP:
        asyncio.run_coroutine_threadsafe(manager.broadcast_new_image(result), GLOBAL_LOOP)
    return result


async def query_image_task(payload: ImageTaskQueryRequest) -> dict[str, Any]:
    provider = provider_store.get_api_provider(payload.provider_id)
    task_id = str(payload.task_id or "").strip()
    timeout = httpx.Timeout(connect=20.0, read=300.0, write=60.0, pool=20.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            raw = await fetch_image_task_payload(client, task_id, provider)
    except httpx.HTTPStatusError as exc:
        text = exc.response.text or ""
        raise HTTPException(status_code=exc.response.status_code, detail=f"查询上游生图任务失败：{text[:300]}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"查询上游生图任务失败：{exc}") from exc

    status = image_task_status(raw)
    image_items: list[dict[str, Any]] = []
    try:
        image_items = extract_images(raw)
    except HTTPException:
        image_items = []
    if image_items:
        local_urls: list[str] = []
        local_items: list[dict[str, Any]] = []
        for item in image_items:
            local_url = await save_ai_image_to_output(item, prefix="online_")
            if local_url:
                local_urls.append(local_url)
                local_items.append(image_output_meta(local_url, item))
        result = {
            "status": "succeeded",
            "prompt": "",
            "images": local_urls,
            "image_items": local_items,
            "timestamp": time.time(),
            "type": "online",
            "model": "",
            "provider_id": provider["id"],
            "provider_name": provider.get("name") or provider["id"],
            "task_id": task_id,
            "request_id": raw.get("id") if isinstance(raw, dict) else "",
            "params": {"provider_id": provider["id"]},
            "raw": raw,
        }
        history_service.save_to_history(result)
        if GLOBAL_LOOP:
            asyncio.run_coroutine_threadsafe(manager.broadcast_new_image(result), GLOBAL_LOOP)
        return result
    if status in IMAGE_TASK_FAILED_STATUSES:
        return {
            "status": "failed",
            "task_id": task_id,
            "provider_id": provider["id"],
            "provider_name": provider.get("name") or provider["id"],
            "error": image_task_fail_reason(raw),
            "raw": raw,
        }
    return {
        "status": "running",
        "task_id": task_id,
        "provider_id": provider["id"],
        "provider_name": provider.get("name") or provider["id"],
        "message": "任务仍在生成中",
        "raw": raw,
    }


async def run_canvas_image_task(task_id: str, payload: OnlineImageRequest) -> None:
    with CANVAS_TASK_LOCK:
        if task_id in CANVAS_TASKS:
            CANVAS_TASKS[task_id]["status"] = "running"
            CANVAS_TASKS[task_id]["updated_at"] = time.time()
    try:
        result = await build_online_image_result(payload)
        with CANVAS_TASK_LOCK:
            CANVAS_TASKS[task_id].update(
                {
                    "status": "succeeded",
                    "result": result,
                    "error": "",
                    "updated_at": time.time(),
                }
            )
    except JimengPendingError as exc:
        info = jimeng_pending_payload(exc)
        with CANVAS_TASK_LOCK:
            CANVAS_TASKS[task_id].update(
                {
                    "status": "jimeng_pending",
                    "jimeng_pending": True,
                    "submit_id": exc.submit_id,
                    "kind": exc.kind,
                    "queue_info": exc.queue_info,
                    "message": info["message"],
                    "error": "",
                    "updated_at": time.time(),
                }
            )
    except Exception as exc:
        detail = getattr(exc, "detail", None) or str(exc)
        status_code = getattr(exc, "status_code", 500)
        upstream_task_id = getattr(exc, "upstream_task_id", "") or extract_task_id_from_text(str(detail))
        with CANVAS_TASK_LOCK:
            CANVAS_TASKS[task_id].update(
                {
                    "status": "failed",
                    "error": str(detail),
                    "status_code": status_code,
                    "upstream_task_id": upstream_task_id,
                    "updated_at": time.time(),
                }
            )


def create_canvas_image_task(payload: OnlineImageRequest) -> dict[str, Any]:
    task_id = f"canvas_img_{uuid.uuid4().hex}"
    with CANVAS_TASK_LOCK:
        CANVAS_TASKS[task_id] = {
            "id": task_id,
            "type": "online-image",
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),
            "result": None,
            "error": "",
            "provider_id": payload.provider_id,
            "model": payload.model,
        }
    asyncio.create_task(run_canvas_image_task(task_id, payload))
    return {"task_id": task_id, "status": "queued"}


def get_canvas_image_task(task_id: str) -> dict[str, Any]:
    with CANVAS_TASK_LOCK:
        task = dict(CANVAS_TASKS.get(task_id) or {})
    if not task:
        raise HTTPException(status_code=404, detail="画布任务不存在，可能服务已重启或任务已过期")
    return task
