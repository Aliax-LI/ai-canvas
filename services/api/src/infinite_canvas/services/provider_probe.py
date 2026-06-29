"""Upstream provider probe and model fetch — httpx async parity with legacy main.py."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException

from infinite_canvas.core.paths import static_runninghub_dir
from infinite_canvas.core.provider_constants import (
    AGNES_DEFAULT_VIDEO_MODELS,
    JIMENG_DEFAULT_IMAGE_MODELS,
    JIMENG_DEFAULT_VIDEO_MODELS,
    RUNNINGHUB_DEFAULT_BASE_URL,
    RUNNINGHUB_DEFAULT_IMAGE_MODELS,
    RUNNINGHUB_DEFAULT_VIDEO_MODELS,
    RUNNINGHUB_FALLBACK_CHAT_MODELS,
    RUNNINGHUB_LLM_MODELS_URLS,
    RUNNINGHUB_MODEL_REGISTRY_URL,
    SUPPORTED_PROVIDER_PROTOCOLS,
)
from infinite_canvas.services import provider_store

STATIC_RUNNINGHUB_MODEL_REGISTRY_FILE = static_runninghub_dir() / "models_registry.json"


from infinite_canvas.services.jimeng import jimeng_status


def looks_like_html_response(text: str) -> bool:
    sample = str(text or "").lstrip()[:200].lower()
    return sample.startswith("<!doctype html") or sample.startswith("<html") or "<head" in sample


def protocol_from_payload(payload: Any) -> str:
    provider_id = str(getattr(payload, "provider_id", "") or "").strip().lower()
    if provider_id == "volcengine":
        return "volcengine"
    if provider_id == "runninghub":
        return "runninghub"
    if provider_id == "jimeng":
        return "jimeng"
    base_url = str(getattr(payload, "base_url", "") or "").strip().lower()
    if "runninghub.cn" in base_url or "runninghub.ai" in base_url:
        return "runninghub"
    protocol = str(getattr(payload, "protocol", "") or "openai").strip().lower()
    return protocol if protocol in SUPPORTED_PROVIDER_PROTOCOLS else "openai"


def api_key_from_payload(payload: Any, protocol: str = "") -> str:
    explicit = str(getattr(payload, "api_key", "") or "").strip()
    provider_id = str(getattr(payload, "provider_id", "") or "").strip().lower()
    protocol = str(protocol or protocol_from_payload(payload) or "").strip().lower()
    if explicit:
        return explicit
    if provider_id:
        if provider_id == "runninghub":
            value = os.getenv(provider_store.runninghub_wallet_key_env(), "")
            if value:
                return value
        value = os.getenv(provider_store.provider_key_env(provider_id), "")
        if value:
            return value
    if protocol == "volcengine":
        return provider_store.volcengine_provider_api_key("")
    return ""


def runninghub_openapi_base_url(provider: dict[str, Any] | None = None) -> str:
    base_url = str((provider or {}).get("base_url") or RUNNINGHUB_DEFAULT_BASE_URL).strip().rstrip("/")
    if base_url.endswith("/openapi/v2"):
        return base_url
    return f"{base_url}/openapi/v2"


def runninghub_openapi_url(provider: dict[str, Any] | None, path: str = "") -> str:
    path = str(path or "").strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    path = path.lstrip("/")
    base = runninghub_openapi_base_url(provider)
    return f"{base}/{path}" if path else base


def upstream_models_url(base_url: str, protocol: str) -> str:
    if protocol == "gemini":
        return f"{base_url}/models" if base_url.endswith("/v1beta") else f"{base_url}/v1beta/models"
    if protocol == "volcengine":
        return f"{base_url}/models" if base_url.endswith("/api/v3") else f"{base_url}/api/v3/models"
    if protocol == "runninghub":
        return runninghub_openapi_url({"base_url": base_url}, "models")
    return f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"


def upstream_model_headers(api_key: str, protocol: str) -> dict[str, str]:
    if protocol == "gemini":
        return {"x-goog-api-key": api_key, "Accept": "application/json"}
    if protocol == "runninghub":
        return {"Authorization": provider_store.bearer_auth_value(api_key), "Accept": "application/json"}
    return {"Authorization": provider_store.bearer_auth_value(api_key), "Accept": "application/json"}


def volcengine_default_model_payload(status: int = 200, message: str = "", raw: Any = None) -> dict[str, Any]:
    return {
        "ok": True,
        "protocol": "volcengine",
        "status": status,
        "message": message
        or "方舟任务接口可用，模型列表接口未返回模型。请按实际方舟控制台模型名称手动填写视频模型。",
        "model_count": 0,
        "image_models": [],
        "chat_models": [],
        "video_models": [],
        "all": [],
        "raw": raw,
    }


def volcengine_task_probe_url(base_url: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/api/v3"):
        return f"{base}/contents/generations/tasks/healthcheck_probe_do_not_submit"
    return f"{base}/api/v3/contents/generations/tasks/healthcheck_probe_do_not_submit"


async def probe_volcengine_task_endpoint(client: httpx.AsyncClient, base_url: str, api_key: str) -> tuple[bool, dict[str, Any]]:
    probe_url = volcengine_task_probe_url(base_url)
    if not probe_url:
        return False, {"status": 0, "message": "Base URL 为空"}
    response = await client.get(probe_url, headers=upstream_model_headers(api_key, "volcengine"))
    try:
        raw = response.json() if response.text else {}
    except Exception:
        raw = response.text[:500]
    if response.status_code in (401, 403):
        return False, {"status": response.status_code, "message": "方舟 API Key 无效或无权限", "raw": raw}
    if looks_like_html_response(response.text):
        return False, {"status": response.status_code, "message": "任务接口返回 HTML，Base URL 可能不是 API 地址", "raw": raw}
    if response.status_code < 500:
        return True, {"status": response.status_code, "message": "方舟任务查询端点可达", "raw": raw}
    return False, {"status": response.status_code, "message": f"方舟任务接口服务端错误 {response.status_code}", "raw": raw}


def openai_compat_root_for_probe(base_url: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if base.endswith("/api/v3"):
        base = base[: -len("/api/v3")]
    if base.endswith("/v1"):
        return base
    return f"{base}/v1" if base else ""


async def probe_openai_compat_bearer_endpoint(
    client: httpx.AsyncClient, base_url: str, api_key: str
) -> tuple[bool, dict[str, Any]]:
    root = openai_compat_root_for_probe(base_url)
    if not root:
        return False, {"status": 0, "message": "Base URL 为空"}
    url = f"{root}/chat/completions"
    response = await client.post(
        url,
        headers={**upstream_model_headers(api_key, "openai"), "Content-Type": "application/json"},
        json={"messages": []},
    )
    try:
        raw = response.json() if response.text else {}
    except Exception:
        raw = response.text[:500]
    if response.status_code in (401, 403):
        return False, {"status": response.status_code, "message": "API Key 无效或无权限", "raw": raw}
    if looks_like_html_response(response.text):
        return False, {"status": response.status_code, "message": "OpenAI 兼容入口返回 HTML，Base URL 可能不是 API 地址", "raw": raw}
    if response.status_code < 500:
        return True, {"status": response.status_code, "message": "OpenAI 兼容 Bearer 鉴权入口可达", "raw": raw}
    return False, {"status": response.status_code, "message": f"OpenAI 兼容入口服务端错误 {response.status_code}", "raw": raw}


def classify_upstream_model(mid: str) -> str:
    lc = str(mid or "").lower()
    video_keys = [
        "veo",
        "sora",
        "wan2",
        "wanx",
        "doubao-seedance",
        "doubao-1",
        "kling",
        "hailuo",
        "video",
        "t2v-",
        "i2v-",
        "s2v",
    ]
    if any(k in lc for k in video_keys):
        return "video"
    image_keys = [
        "banana",
        "image",
        "dalle",
        "dall-e",
        "imagen",
        "flux",
        "stable",
        "sdxl",
        "midjourney",
        "nano-banana",
        "ideogram",
        "fal-ai",
        "z-image",
        "qwen-image",
        "klein",
        "seedream",
        "doubao-seedream",
        "text-to-image",
        "image-to-image",
    ]
    if any(k in lc for k in image_keys):
        return "image"
    return "chat"


def parse_upstream_models(raw: dict[str, Any], protocol: str = "openai") -> tuple[dict[str, list[str]], list[str]]:
    items = raw.get("data") if isinstance(raw, dict) else None
    if not items and isinstance(raw, dict):
        items = raw.get("models") or raw.get("list") or []
    if not isinstance(items, list):
        items = []
    ids: list[str] = []
    for it in items:
        if isinstance(it, str):
            mid = it
        elif isinstance(it, dict):
            mid = it.get("id") or it.get("name") or it.get("model")
        else:
            mid = ""
        if mid:
            mid = str(mid)
            if protocol == "gemini" and mid.startswith("models/"):
                mid = mid[len("models/") :]
            ids.append(mid)
    ids = sorted(set(ids))
    grouped: dict[str, list[str]] = {"image": [], "chat": [], "video": []}
    for mid in ids:
        grouped[classify_upstream_model(mid)].append(mid)
    return grouped, ids


def apply_agnes_model_defaults(
    base_url: str, grouped: dict[str, list[str]], ids: list[str]
) -> tuple[dict[str, list[str]], list[str]]:
    if "apihub.agnes-ai.com" not in str(base_url or "").strip().lower():
        return grouped, ids
    grouped = {key: list(value or []) for key, value in (grouped or {}).items()}
    ids = list(ids or [])
    for model in AGNES_DEFAULT_VIDEO_MODELS:
        if model not in ids:
            ids.append(model)
        if model not in grouped.setdefault("video", []):
            grouped["video"].append(model)
    ids = sorted(set(ids))
    grouped["video"] = sorted(set(grouped.get("video") or []))
    return grouped, ids


async def probe_openai_models_endpoint(
    client: httpx.AsyncClient, base_url: str, api_key: str
) -> tuple[bool, dict[str, Any]]:
    url = upstream_models_url(base_url, "openai")
    response = await client.get(url, headers=upstream_model_headers(api_key, "openai"))
    try:
        raw = response.json() if response.text else {}
    except Exception:
        raw = response.text[:500]
    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("Location") or response.headers.get("location") or ""
        suffix = f"：{location}" if location else ""
        return False, {
            "status": response.status_code,
            "message": f"OpenAI /v1/models 发生跳转{suffix}，请填写 API Base URL，不要填写网页登录地址",
            "raw": raw,
        }
    if response.status_code in (401, 403):
        return False, {"status": response.status_code, "message": "OpenAI API Key 无效或无权限", "raw": raw}
    if looks_like_html_response(response.text):
        return False, {
            "status": response.status_code,
            "message": "OpenAI /v1/models 返回网页 HTML，请检查请求地址是否为 API Base URL",
            "raw": raw,
        }
    if response.status_code < 300:
        grouped, ids = parse_upstream_models(raw, "openai") if isinstance(raw, dict) else ({"image": [], "chat": [], "video": []}, [])
        grouped, ids = apply_agnes_model_defaults(base_url, grouped, ids)
        return True, {
            "status": response.status_code,
            "message": f"OpenAI 兼容模型列表端点可用{f'，找到 {len(ids)} 个模型' if ids else ''}",
            "raw": raw,
            "model_count": len(ids),
            "image_models": grouped["image"],
            "chat_models": grouped["chat"],
            "video_models": grouped["video"],
            "all": ids,
        }
    if 400 <= response.status_code < 500:
        return False, {"status": response.status_code, "message": f"OpenAI /v1/models 不可用 (HTTP {response.status_code})", "raw": raw}
    return False, {"status": response.status_code, "message": f"OpenAI /v1/models 服务端错误 {response.status_code}", "raw": raw}


async def probe_volcengine_auto_detect(
    client: httpx.AsyncClient, base_url: str, api_key: str
) -> tuple[bool, dict[str, Any]]:
    task_ok, task_probe = await probe_volcengine_task_endpoint(client, base_url, api_key)
    if task_ok:
        return True, {
            "status": task_probe.get("status") or 200,
            "message": "检测到方舟/Ark 任务协议",
            "raw": {"task_probe": task_probe.get("raw")},
        }
    compat_ok, compat_probe = await probe_openai_compat_bearer_endpoint(client, base_url, api_key)
    if compat_ok:
        return True, {
            "status": compat_probe.get("status") or 200,
            "message": "检测到方舟/Ark Bearer 鉴权入口（OpenAI 兼容透传）",
            "raw": {"task_probe": task_probe, "openai_compat_probe": compat_probe.get("raw")},
        }
    return False, {
        "status": compat_probe.get("status") or task_probe.get("status") or 0,
        "message": compat_probe.get("message") or task_probe.get("message") or "未检测到方舟/Ark 兼容入口",
        "raw": {"task_probe": task_probe, "openai_compat_probe": compat_probe.get("raw")},
    }


def runninghub_api_headers(provider: dict[str, Any] | None) -> dict[str, str]:
    api_key = str((provider or {}).get("api_key") or "").strip()
    if not api_key:
        api_key = provider_store.provider_env_key_value(str((provider or {}).get("id") or "runninghub"))
    if not api_key:
        return {"Accept": "application/json"}
    return {
        "Authorization": provider_store.bearer_auth_value(api_key),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def runninghub_registry_fallback() -> list[dict[str, Any]]:
    image = [
        {"name_en": "gpt-image-2/text-to-image-official-stable", "endpoint": "rhart-image-g-2-official/text-to-image", "output_type": "image"},
        {"name_en": "gpt-image-2/image-to-image-official-stable", "endpoint": "rhart-image-g-2-official/image-to-image", "output_type": "image"},
        {"name_en": "nano-banana/text-to-image-official-stable", "endpoint": "rhart-image-v1-official/text-to-image", "output_type": "image"},
        {"name_en": "nano-banana/edit-official-stable", "endpoint": "rhart-image-v1-official/edit", "output_type": "image"},
    ]
    video = [
        {"name_en": "google/veo3.1-fast/text-to-video-channel-low-price", "endpoint": "rhart-video-v3.1-fast/text-to-video", "output_type": "video"},
        {"name_en": "sora-2/text-to-video-official-stable", "endpoint": "rhart-video-s-official/text-to-video", "output_type": "video"},
        {"name_en": "seedance-2.0-global/text-to-video", "endpoint": "bytedance/seedance-2.0-global/text-to-video", "output_type": "video"},
        {"name_en": "seedance-2.0-global/image-to-video", "endpoint": "bytedance/seedance-2.0-global/image-to-video", "output_type": "video"},
    ]
    return image + video


def runninghub_registry_items_from_raw(raw: Any) -> list[dict[str, Any]]:
    candidates = [raw]
    if isinstance(raw, dict):
        candidates.extend([raw.get("data"), raw.get("models"), raw.get("list"), raw.get("items"), raw.get("records"), raw.get("result")])
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
        if isinstance(candidate, dict):
            nested = (
                candidate.get("models")
                or candidate.get("list")
                or candidate.get("items")
                or candidate.get("records")
                or candidate.get("data")
            )
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def runninghub_model_id(item: dict[str, Any] | None) -> str:
    if not isinstance(item, dict):
        return ""
    return str(item.get("name_en") or item.get("id") or item.get("name") or item.get("endpoint") or "").strip()


def runninghub_registry_model_from_id(model_id: str, output_type: str = "") -> dict[str, Any]:
    model_id = str(model_id or "").strip()
    if not model_id:
        return {}
    output_type = str(output_type or "").strip().lower() or classify_upstream_model(model_id)
    return {"name_en": model_id, "endpoint": model_id, "output_type": output_type}


async def fetch_runninghub_llm_models(provider: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    headers = runninghub_api_headers(provider)
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for url in RUNNINGHUB_LLM_MODELS_URLS:
            try:
                resp = await client.get(url, headers=headers)
                if resp.status_code >= 400 or looks_like_html_response(resp.text):
                    errors.append(f"{url}: HTTP {resp.status_code} {resp.text[:180]}")
                    continue
                raw = resp.json() if resp.text else {}
                grouped, ids = parse_upstream_models(raw, "openai")
                if ids:
                    return [runninghub_registry_model_from_id(mid, "chat") for mid in ids], {"source": url, "count": len(ids)}
                errors.append(f"{url}: empty")
            except Exception as exc:
                errors.append(f"{url}: {str(exc)[:180]}")
    return [], {"source": "", "count": 0, "errors": errors[-3:]}


async def fetch_runninghub_model_registry(
    provider: dict[str, Any] | None = None,
    include_fallback: bool = True,
    include_meta: bool = False,
) -> Any:
    urls: list[tuple[str, str]] = [
        ("openapi", runninghub_openapi_url(provider, "models")),
        ("github", RUNNINGHUB_MODEL_REGISTRY_URL),
    ]
    if STATIC_RUNNINGHUB_MODEL_REGISTRY_FILE.is_file():
        urls.append(("local", str(STATIC_RUNNINGHUB_MODEL_REGISTRY_FILE)))
    headers = runninghub_api_headers(provider)
    errors: list[str] = []
    source = ""
    items: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for source_name, url in urls:
            try:
                if source_name == "local":
                    raw = json.loads(Path(url).read_text(encoding="utf-8"))
                else:
                    req_headers = headers if source_name == "openapi" else {"Accept": "application/json"}
                    resp = await client.get(url, headers=req_headers)
                    if resp.status_code >= 400 or looks_like_html_response(resp.text):
                        errors.append(f"{source_name}: HTTP {resp.status_code} {resp.text[:180]}")
                        continue
                    raw = resp.json() if resp.text else []
                parsed = runninghub_registry_items_from_raw(raw)
                if parsed:
                    items = parsed
                    source = source_name
                    break
                errors.append(f"{source_name}: empty")
            except Exception as exc:
                errors.append(f"{source_name}: {str(exc)[:180]}")
                continue
    llm_items, llm_meta = await fetch_runninghub_llm_models(provider)
    combined = [*items]
    seen = {runninghub_model_id(item) for item in combined if runninghub_model_id(item)}
    for item in llm_items:
        mid = runninghub_model_id(item)
        if mid and mid not in seen:
            combined.append(item)
            seen.add(mid)
    if combined:
        meta = {
            "source": source or "llm",
            "openapi_count": len(items),
            "llm_count": len(llm_items),
            "llm_source": llm_meta.get("source") or "",
            "errors": [*errors[-3:], *((llm_meta.get("errors") or [])[-3:])],
        }
        return (combined, meta) if include_meta else combined
    if include_fallback:
        fallback = runninghub_registry_fallback()
        meta = {
            "source": "fallback",
            "openapi_count": 0,
            "llm_count": 0,
            "llm_source": "",
            "errors": [*errors[-3:], *((llm_meta.get("errors") or [])[-3:])],
        }
        return (fallback, meta) if include_meta else fallback
    raise HTTPException(status_code=502, detail=f"拉取 RunningHub 模型注册表失败：{'; '.join(errors[-4:]) or 'unknown error'}")


def runninghub_registry_payload(items: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[str]] = {"image": [], "chat": RUNNINGHUB_FALLBACK_CHAT_MODELS[:], "video": []}
    all_ids: list[str] = []
    for item in items or []:
        mid = runninghub_model_id(item)
        if not mid:
            continue
        output_type = str(item.get("output_type") or item.get("outputType") or "").strip().lower()
        if output_type in ("image", "video"):
            grouped[output_type].append(mid)
            all_ids.append(mid)
    for model in RUNNINGHUB_DEFAULT_IMAGE_MODELS:
        if model not in grouped["image"]:
            grouped["image"].append(model)
            all_ids.append(model)
    for model in RUNNINGHUB_DEFAULT_VIDEO_MODELS:
        if model not in grouped["video"]:
            grouped["video"].append(model)
            all_ids.append(model)
    for model in RUNNINGHUB_FALLBACK_CHAT_MODELS:
        if model not in all_ids:
            all_ids.append(model)
    for key in grouped:
        grouped[key] = sorted(set(grouped[key]))
    return {
        "total": len(set(all_ids)),
        "image_models": grouped["image"],
        "chat_models": grouped["chat"],
        "video_models": grouped["video"],
        "all": sorted(set(all_ids)),
        "protocol": "runninghub",
    }


async def runninghub_models_payload(provider: dict[str, Any] | None = None) -> dict[str, Any]:
    registry, meta = await fetch_runninghub_model_registry(provider, include_fallback=True, include_meta=True)
    payload = runninghub_registry_payload(registry)
    payload["raw"] = {"registry_count": len(registry), **meta}
    if meta.get("source") == "fallback":
        payload["message"] = "RunningHub 模型接口未返回完整列表，当前显示内置兜底模型。"
    else:
        payload["message"] = f"RunningHub 模型列表来自 {meta.get('source')}"
    return payload


async def test_provider_connection(payload: Any) -> dict[str, Any]:
    protocol = protocol_from_payload(payload)
    if protocol == "jimeng":
        status = await jimeng_status()
        return {
            "ok": bool(status.get("installed") and status.get("logged_in")),
            "status": 200 if status.get("logged_in") else 0,
            "message": status.get("message") or "即梦 CLI 已登录",
            "model_count": len(JIMENG_DEFAULT_IMAGE_MODELS) + len(JIMENG_DEFAULT_VIDEO_MODELS),
            "image_models": JIMENG_DEFAULT_IMAGE_MODELS,
            "chat_models": [],
            "video_models": JIMENG_DEFAULT_VIDEO_MODELS,
            "all": [*JIMENG_DEFAULT_IMAGE_MODELS, *JIMENG_DEFAULT_VIDEO_MODELS],
            "raw": status.get("raw"),
        }
    if protocol == "runninghub":
        provider = {
            "id": "runninghub",
            "name": "RunningHub",
            "base_url": (payload.base_url or RUNNINGHUB_DEFAULT_BASE_URL).strip().rstrip("/"),
            "protocol": "runninghub",
            "api_key": api_key_from_payload(payload, protocol),
        }
        payload_models = await runninghub_models_payload(provider)
        return {
            "ok": True,
            "status": 200,
            "message": "RunningHub OpenAPI 可用，已拉取官方直连模型注册表。",
            "model_count": payload_models["total"],
            "image_models": payload_models["image_models"],
            "chat_models": payload_models["chat_models"],
            "video_models": payload_models["video_models"],
            "all": payload_models["all"],
            "protocol": "runninghub",
            "raw": payload_models.get("raw"),
        }
    base_url = (payload.base_url or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="请先填写请求地址")
    if not re.match(r"^https?://", base_url):
        raise HTTPException(status_code=400, detail="请求地址必须以 http:// 或 https:// 开头")
    api_key = api_key_from_payload(payload, protocol)
    if not api_key:
        key_name = "方舟 API Key" if protocol == "volcengine" else "API Key"
        raise HTTPException(status_code=400, detail=f"请先填写或保存 {key_name}")
    url = upstream_models_url(base_url, protocol)
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=upstream_model_headers(api_key, protocol))
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location") or resp.headers.get("location") or ""
                suffix = f"：{location}" if location else ""
                endpoint_label = (
                    "/v1beta/models"
                    if protocol == "gemini"
                    else "/api/v3/models"
                    if protocol == "volcengine"
                    else "/openapi/v2/models"
                    if protocol == "runninghub"
                    else "/v1/models"
                )
                return {
                    "ok": False,
                    "status": resp.status_code,
                    "message": f"上游 {endpoint_label} 发生跳转{suffix}，请填写 API Base URL，不要填写网页登录地址",
                }
            if looks_like_html_response(resp.text):
                endpoint_label = (
                    "/v1beta/models"
                    if protocol == "gemini"
                    else "/api/v3/models"
                    if protocol == "volcengine"
                    else "/openapi/v2/models"
                    if protocol == "runninghub"
                    else "/v1/models"
                )
                return {
                    "ok": False,
                    "status": resp.status_code,
                    "message": f"上游 {endpoint_label} 返回网页 HTML，请检查请求地址是否为 API Base URL",
                }
            if resp.status_code >= 400:
                if protocol == "volcengine":
                    detected, probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                    if detected:
                        message = f"{probe.get('message') or '方舟任务接口可达'}；但 /api/v3/models 不可用。请按实际方舟控制台模型名称手动填写视频模型。"
                        return volcengine_default_model_payload(
                            status=probe.get("status") or resp.status_code,
                            message=message,
                            raw={"models_error": resp.text[:300], **(probe.get("raw") or {})},
                        )
                elif protocol == "openai":
                    detected, probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                    if detected:
                        message = f"{probe.get('message') or '检测到方舟/Ark 兼容入口'}；OpenAI /v1/models 不可用，已自动切换为方舟协议。请按实际方舟控制台模型名称手动填写视频模型。"
                        return volcengine_default_model_payload(
                            status=probe.get("status") or resp.status_code,
                            message=message,
                            raw={"models_error": resp.text[:300], **(probe.get("raw") or {})},
                        )
                return {"ok": False, "status": resp.status_code, "message": resp.text[:300]}
            data = resp.json() if resp.text else {}
            grouped, ids = parse_upstream_models(data, protocol)
            grouped, ids = apply_agnes_model_defaults(base_url, grouped, ids)
            if protocol == "volcengine" and not ids:
                detected, probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                if detected:
                    return volcengine_default_model_payload(status=resp.status_code, raw=data)
            return {
                "ok": True,
                "status": resp.status_code,
                "model_count": len(ids),
                "image_models": grouped["image"],
                "chat_models": grouped["chat"],
                "video_models": grouped["video"],
                "all": ids,
                "image_request_mode": provider_store.detect_image_request_mode(base_url, ids)
                or provider_store.normalize_image_request_mode(getattr(payload, "image_request_mode", "")),
            }
    except httpx.HTTPError as exc:
        if protocol == "volcengine":
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    detected, probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                    if detected:
                        message = f"{probe.get('message') or '方舟任务接口可达'}；但模型列表请求失败。请按实际方舟控制台模型名称手动填写视频模型。"
                        return volcengine_default_model_payload(
                            status=probe.get("status") or 0,
                            message=message,
                            raw={"models_error": str(exc)[:300], **(probe.get("raw") or {})},
                        )
            except Exception:
                pass
        return {"ok": False, "status": 0, "message": str(exc)[:300]}


async def probe_async_endpoint(payload: Any) -> dict[str, Any]:
    base_url = (payload.base_url or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="请先填写请求地址")
    protocol = protocol_from_payload(payload)
    api_key = api_key_from_payload(payload, protocol)
    if not api_key:
        raise HTTPException(status_code=400, detail="请先填写或保存 API Key")
    if protocol == "volcengine":
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                task_ok, task_probe = await probe_volcengine_task_endpoint(client, base_url, api_key)
                if task_ok:
                    return {
                        "ok": True,
                        "protocol": "volcengine",
                        "status_code": task_probe.get("status") or 200,
                        "message": "方舟/Ark 任务协议可用",
                        "raw": task_probe.get("raw"),
                    }
                compat_ok, compat_probe = await probe_openai_compat_bearer_endpoint(client, base_url, api_key)
                if compat_ok:
                    return {
                        "ok": True,
                        "protocol": "volcengine",
                        "status_code": compat_probe.get("status") or 200,
                        "message": "方舟/Ark Bearer 鉴权入口可用（OpenAI 兼容透传）",
                        "raw": {"task_probe": task_probe, "openai_compat_probe": compat_probe.get("raw")},
                    }
                return {
                    "ok": False,
                    "protocol": "volcengine",
                    "status_code": compat_probe.get("status") or task_probe.get("status") or 0,
                    "message": compat_probe.get("message") or task_probe.get("message") or "方舟/Ark 任务协议不可用",
                    "raw": {"task_probe": task_probe, "openai_compat_probe": compat_probe.get("raw")},
                }
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=str(exc)[:300]) from exc
    tasks_base = base_url if base_url.endswith("/v1") else f"{base_url}/v1"
    probe_url = f"{tasks_base}/tasks/healthcheck_probe_do_not_submit"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                probe_url,
                headers={"Authorization": provider_store.bearer_auth_value(api_key), "Accept": "application/json"},
            )
            try:
                body = resp.json()
            except Exception:
                body = resp.text[:500]
            sc = resp.status_code
            err_msg = ""
            if isinstance(body, dict):
                err = body.get("error") or {}
                if isinstance(err, dict):
                    err_msg = str(err.get("message") or "").lower()
                else:
                    err_msg = str(err).lower()
            if sc == 400 and "invalid task id" in err_msg:
                return {
                    "ok": True,
                    "protocol": "apimart",
                    "status_code": sc,
                    "message": "APIMart 异步任务端点可用，API Key 已通过认证",
                    "raw": body,
                }
            async_probe: dict[str, Any] = {"status": sc, "message": "", "raw": body}
            if sc in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location") or resp.headers.get("location") or ""
                async_probe["message"] = f"/v1/tasks/ 发生跳转{f'：{location}' if location else ''}"
            elif looks_like_html_response(resp.text):
                async_probe["message"] = "/v1/tasks/ 返回网页 HTML"
            elif sc in (401, 403):
                async_probe["message"] = "/v1/tasks/ 返回鉴权失败"
            elif sc == 404:
                async_probe["message"] = "平台不支持 /v1/tasks/ 端点，可能不是 APIMart 异步协议"
            elif 400 <= sc < 500:
                async_probe["message"] = f"/v1/tasks/ 返回 {sc}"
            elif sc < 300:
                async_probe["message"] = f"/v1/tasks/ 返回 {sc}（意外成功）"
            else:
                async_probe["message"] = f"/v1/tasks/ 服务端错误 {sc}"
            if protocol == "apimart":
                return {"ok": False, "protocol": "apimart", "status_code": sc, "message": async_probe["message"], "raw": body}
            openai_ok, openai_probe = await probe_openai_models_endpoint(client, base_url, api_key)
            if not openai_ok and protocol == "openai":
                compat_ok, compat_probe = await probe_openai_compat_bearer_endpoint(client, base_url, api_key)
                if compat_ok and (compat_probe.get("status") or 0) != 404:
                    return {
                        "ok": True,
                        "protocol": "openai",
                        "status_code": compat_probe.get("status") or openai_probe.get("status") or sc,
                        "message": "OpenAI 兼容入口可达（该站未提供 /v1/models，模型请手动填写）",
                        "raw": {
                            "async_probe": async_probe,
                            "openai_probe": openai_probe.get("raw"),
                            "openai_compat_probe": compat_probe.get("raw"),
                        },
                        "model_count": 0,
                        "image_models": [],
                        "chat_models": [],
                        "video_models": [],
                        "all": [],
                    }
                detected, volc_probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                if detected:
                    return {
                        "ok": True,
                        "protocol": "volcengine",
                        "status_code": volc_probe.get("status") or openai_probe.get("status") or sc,
                        "message": f"{volc_probe.get('message') or '检测到方舟/Ark 兼容入口'}，已自动切换为方舟/Ark 任务协议",
                        "raw": {"async_probe": async_probe, "openai_probe": openai_probe.get("raw"), **(volc_probe.get("raw") or {})},
                    }
            return {
                "ok": openai_ok,
                "protocol": "openai",
                "status_code": openai_probe.get("status") or sc,
                "message": openai_probe.get("message") or "OpenAI 兼容验证完成",
                "raw": {"async_probe": async_probe, "openai_probe": openai_probe.get("raw")},
                "model_count": openai_probe.get("model_count") or 0,
                "image_models": openai_probe.get("image_models") or [],
                "chat_models": openai_probe.get("chat_models") or [],
                "video_models": openai_probe.get("video_models") or [],
                "all": openai_probe.get("all") or [],
                "image_request_mode": provider_store.detect_image_request_mode(base_url, openai_probe.get("all") or [])
                or provider_store.normalize_image_request_mode(getattr(payload, "image_request_mode", "")),
            }
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)[:300]) from exc


async def fetch_models_from_upstream(
    base_url: str,
    api_key: str,
    protocol: str = "openai",
    image_request_mode: str = "openai",
) -> dict[str, Any]:
    protocol = protocol if protocol in SUPPORTED_PROVIDER_PROTOCOLS else "openai"
    if protocol == "jimeng":
        return {
            "total": len(JIMENG_DEFAULT_IMAGE_MODELS) + len(JIMENG_DEFAULT_VIDEO_MODELS),
            "image_models": JIMENG_DEFAULT_IMAGE_MODELS,
            "chat_models": [],
            "video_models": JIMENG_DEFAULT_VIDEO_MODELS,
            "all": [*JIMENG_DEFAULT_IMAGE_MODELS, *JIMENG_DEFAULT_VIDEO_MODELS],
        }
    if protocol == "runninghub":
        provider = {
            "id": "runninghub",
            "name": "RunningHub",
            "base_url": base_url or RUNNINGHUB_DEFAULT_BASE_URL,
            "protocol": "runninghub",
            "api_key": api_key,
        }
        return await runninghub_models_payload(provider)
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise HTTPException(status_code=400, detail="请先填写请求地址")
    if not re.match(r"^https?://", base_url):
        raise HTTPException(status_code=400, detail="请求地址必须以 http:// 或 https:// 开头")
    api_key = provider_store.volcengine_provider_api_key(api_key) if protocol == "volcengine" else (api_key or "").strip()
    if not api_key:
        key_name = "方舟 API Key" if protocol == "volcengine" else "API Key"
        raise HTTPException(status_code=400, detail=f"请先填写或保存 {key_name}")
    url = upstream_models_url(base_url, protocol)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=upstream_model_headers(api_key, protocol))
            endpoint_label = (
                "/v1beta/models"
                if protocol == "gemini"
                else "/api/v3/models"
                if protocol == "volcengine"
                else "/openapi/v2/models"
                if protocol == "runninghub"
                else "/v1/models"
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location") or resp.headers.get("location") or ""
                suffix = f"：{location}" if location else ""
                raise HTTPException(
                    status_code=400,
                    detail=f"上游 {endpoint_label} 发生跳转{suffix}，请填写 API Base URL，不要填写网页登录地址",
                )
            if looks_like_html_response(resp.text):
                raise HTTPException(
                    status_code=400,
                    detail=f"上游 {endpoint_label} 返回网页 HTML，请检查请求地址是否为 API Base URL",
                )
            if resp.status_code >= 400:
                if protocol == "volcengine":
                    detected, probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                    if detected:
                        payload = volcengine_default_model_payload(
                            status=probe.get("status") or resp.status_code,
                            message=f"{probe.get('message') or '方舟任务接口可达'}；但 /api/v3/models 不可用。请按实际方舟控制台模型名称手动填写视频模型。",
                            raw={"models_error": resp.text[:300], **(probe.get("raw") or {})},
                        )
                        return {
                            "total": payload["model_count"],
                            "protocol": payload["protocol"],
                            "image_models": payload["image_models"],
                            "chat_models": payload["chat_models"],
                            "video_models": payload["video_models"],
                            "all": payload["all"],
                            "message": payload["message"],
                            "raw": payload["raw"],
                        }
                elif protocol == "openai":
                    detected, probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                    if detected:
                        payload = volcengine_default_model_payload(
                            status=probe.get("status") or resp.status_code,
                            message=f"{probe.get('message') or '检测到方舟/Ark 兼容入口'}；OpenAI /v1/models 不可用，已自动切换为方舟协议。请按实际方舟控制台模型名称手动填写视频模型。",
                            raw={"models_error": resp.text[:300], **(probe.get("raw") or {})},
                        )
                        return {
                            "total": payload["model_count"],
                            "protocol": payload["protocol"],
                            "image_models": payload["image_models"],
                            "chat_models": payload["chat_models"],
                            "video_models": payload["video_models"],
                            "all": payload["all"],
                            "message": payload["message"],
                            "raw": payload["raw"],
                        }
                raise HTTPException(status_code=resp.status_code, detail=f"上游 {endpoint_label} 失败：{resp.text[:300]}")
            raw = resp.json()
    except httpx.HTTPError as exc:
        if protocol == "volcengine":
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    detected, probe = await probe_volcengine_auto_detect(client, base_url, api_key)
                    if detected:
                        payload = volcengine_default_model_payload(
                            status=probe.get("status") or 0,
                            message=f"{probe.get('message') or '方舟任务接口可达'}；但模型列表请求失败。请按实际方舟控制台模型名称手动填写视频模型。",
                            raw={"models_error": str(exc)[:300], **(probe.get("raw") or {})},
                        )
                        return {
                            "total": payload["model_count"],
                            "protocol": payload["protocol"],
                            "image_models": payload["image_models"],
                            "chat_models": payload["chat_models"],
                            "video_models": payload["video_models"],
                            "all": payload["all"],
                            "message": payload["message"],
                            "raw": payload["raw"],
                        }
            except Exception:
                pass
        raise HTTPException(status_code=502, detail=f"请求上游模型列表失败：{exc}") from exc
    grouped, ids = parse_upstream_models(raw, protocol)
    grouped, ids = apply_agnes_model_defaults(base_url, grouped, ids)
    if protocol == "volcengine" and not ids:
        payload = volcengine_default_model_payload(raw=raw)
        return {
            "total": payload["model_count"],
            "image_models": payload["image_models"],
            "chat_models": payload["chat_models"],
            "video_models": payload["video_models"],
            "all": payload["all"],
            "message": payload["message"],
            "raw": payload["raw"],
        }
    return {
        "total": len(ids),
        "image_models": grouped["image"],
        "chat_models": grouped["chat"],
        "video_models": grouped["video"],
        "all": ids,
        "image_request_mode": provider_store.detect_image_request_mode(base_url, ids)
        or provider_store.normalize_image_request_mode(image_request_mode),
    }
