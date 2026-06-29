"""Vision caption and classification via upstream chat providers — legacy parity."""

from __future__ import annotations

import base64
import os
from io import BytesIO
from typing import Any

import httpx
from fastapi import HTTPException
from PIL import Image

from infinite_canvas.core.asset_utils import (
    asset_classification_prompt,
    content_type_for_path,
    normalize_asset_classification,
    parse_asset_classification_text,
)
from infinite_canvas.core.provider_constants import (
    FIXED_PROTOCOL_PROVIDER_IDS,
    MODELSCOPE_CHAT_BASE_URL,
    PER_MODEL_PROTOCOL_OPTIONS,
    RUNNINGHUB_LLM_BASE_URL,
)
from infinite_canvas.core.runtime_config import AI_API_KEY, AI_BASE_URL, CHAT_MODEL, MODELSCOPE_CHAT_MODELS
from infinite_canvas.services import provider_store

AI_REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "1800"))


def selected_model(requested: str, fallback: str) -> str:
    model = (requested or fallback).strip()
    if not model:
        raise HTTPException(status_code=400, detail="模型名称不能为空")
    if len(model) > 240 or any(ord(ch) < 32 or ord(ch) == 127 for ch in model):
        raise HTTPException(status_code=400, detail=f"模型名称不合法：{model}")
    return model


def effective_protocol(provider: dict[str, Any], model: str = "") -> str:
    base = provider_store.provider_protocol(provider)
    pid = str((provider or {}).get("id") or "").strip().lower()
    if pid in FIXED_PROTOCOL_PROVIDER_IDS:
        return base
    overrides = (provider or {}).get("model_protocols")
    if isinstance(overrides, dict):
        val = str(overrides.get(str(model or "").strip()) or "").strip().lower()
        if val in PER_MODEL_PROTOCOL_OPTIONS:
            return val
    return base


def is_apimart_provider(provider: dict[str, Any] | None) -> bool:
    base_url = str((provider or {}).get("base_url") or "").lower()
    return provider_store.provider_protocol(provider) == "apimart" or "apimart.ai" in base_url


def is_volcengine_provider(provider: dict[str, Any] | None) -> bool:
    return provider_store.provider_protocol(provider) == "volcengine"


def looks_like_vision_chat_model(model: str) -> bool:
    lc = str(model or "").strip().lower()
    if not lc:
        return False
    vision_keys = [
        "vision",
        "vl-",
        "-vl-",
        "internvl",
        "qvq",
        "qwen-vl",
        "doubao-vision",
        "glm-4v",
        "minicpm-v",
    ]
    return any(key in lc for key in vision_keys)


def preferred_chat_model(provider: dict[str, Any]) -> str:
    values = [str(item or "").strip() for item in (provider.get("chat_models") or [CHAT_MODEL])]
    models = [item for item in values if item]
    if not models:
        return CHAT_MODEL
    if is_volcengine_provider(provider):
        endpoint_models = [item for item in models if item.lower().startswith("ep-")]
        if endpoint_models:
            return endpoint_models[0]
        text_like_models = [item for item in models if not looks_like_vision_chat_model(item)]
        if text_like_models:
            return text_like_models[0]
    return models[0]


def modelscope_api_root(provider: dict[str, Any] | None = None) -> str:
    provider = provider or provider_store.get_api_provider_exact("modelscope")
    base_root = str((provider or {}).get("base_url") or MODELSCOPE_CHAT_BASE_URL).strip().rstrip("/")
    if not base_root:
        base_root = MODELSCOPE_CHAT_BASE_URL
    return base_root if base_root.endswith("/v1") else f"{base_root}/v1"


def api_headers(json_body: bool = True, provider: dict[str, Any] | None = None, model: str = "") -> dict[str, str]:
    if provider:
        key_env = provider_store.provider_key_env(provider["id"])
        api_key = os.getenv(key_env, "")
        provider_name = provider.get("name") or provider["id"]
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail=f"未配置 {provider_name} 的 API Key，请在 API 平台管理中填写。",
            )
    else:
        api_key = AI_API_KEY
        if not api_key:
            raise HTTPException(status_code=400, detail="未配置 COMFLY_API_KEY，请在 API/.env 中填写。")
    if provider and effective_protocol(provider, model) == "gemini":
        headers = {"Accept": "application/json", "x-goog-api-key": api_key}
    else:
        headers = {"Accept": "application/json", "Authorization": provider_store.bearer_auth_value(api_key)}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def resolve_chat_provider(provider: str, model: str, ms_model: str) -> tuple[str, dict[str, str], str]:
    if provider == "modelscope":
        clean_token = provider_store.modelscope_api_key()
        if not clean_token:
            raise HTTPException(status_code=400, detail="未配置 ModelScope API Key，请在 API 设置中填写。")
        base = modelscope_api_root()
        hdrs = {
            "Authorization": provider_store.bearer_auth_value(clean_token),
            "Content-Type": "application/json",
        }
        default_ms = MODELSCOPE_CHAT_MODELS[0] if MODELSCOPE_CHAT_MODELS else "MiniMax/MiniMax-M2.7"
        mdl = selected_model(ms_model or model, default_ms)
        return base, hdrs, mdl
    api_provider = provider_store.get_api_provider(provider or "")
    base_root = (api_provider.get("base_url") or AI_BASE_URL).rstrip("/")
    if not base_root:
        raise HTTPException(
            status_code=400,
            detail=f"{api_provider.get('name') or api_provider['id']} 未配置 Base URL",
        )
    default_model = preferred_chat_model(api_provider)
    mdl = selected_model(model, default_model)
    protocol = effective_protocol(api_provider, mdl)
    if protocol == "gemini":
        base = base_root if base_root.endswith("/v1beta") else base_root + "/v1beta"
    elif protocol == "volcengine":
        base = base_root if base_root.endswith("/api/v3") else base_root + "/api/v3"
    elif protocol == "runninghub":
        base = RUNNINGHUB_LLM_BASE_URL
    else:
        base = base_root if base_root.endswith("/v1") else base_root + "/v1"
    hdrs = api_headers(provider=api_provider, model=mdl)
    return base, hdrs, mdl


def unwrap_apimart_response(raw: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict) and "data" in raw and isinstance(raw.get("data"), dict) and "choices" not in raw:
        return raw["data"]
    return raw


def text_from_chat_response(data: dict[str, Any]) -> str:
    data = unwrap_apimart_response(data)
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text") or item.get("content") or "")
        return "\n".join(part for part in parts if part)
    return str(content)


def image_path_to_data_url(path: str, max_size: int = 1024) -> str:
    if max_size:
        try:
            with Image.open(path) as img:
                img.load()
                if max(img.size) > max_size:
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
            print(f"shared caption image resize failed: {exc}")
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{content_type_for_path(path)};base64,{encoded}"


async def caption_image_with_provider(
    abs_path: str,
    prompt: str,
    provider_id: str,
    model: str,
    ms_model: str = "",
) -> tuple[str, str]:
    chat_base, chat_hdrs, resolved_model = resolve_chat_provider(provider_id, model, ms_model)
    llm_provider = provider_store.get_api_provider(provider_id) if provider_id not in ("modelscope",) else {}
    is_apimart = is_apimart_provider(llm_provider)
    prompt_text = (prompt or "描述图片").strip() or "描述图片"
    data_url = image_path_to_data_url(abs_path, max_size=1024)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    raw: dict[str, Any] | None = None
    try:
        async with httpx.AsyncClient(timeout=AI_REQUEST_TIMEOUT) as client:
            req_body: dict[str, Any] = {"model": resolved_model, "messages": messages}
            if is_apimart:
                req_body["stream"] = False
            response = await client.post(
                f"{chat_base}/chat/completions",
                headers=chat_hdrs,
                json=req_body,
            )
            response.raise_for_status()
            raw = response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text or ""
        raise HTTPException(status_code=exc.response.status_code, detail=body or "上游接口错误") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"请求上游接口失败：{exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"解析上游响应失败：{exc}") from exc
    text = text_from_chat_response(raw).strip() if isinstance(raw, dict) else ""
    return text or "接口返回了空回复。", resolved_model


async def classify_image_with_provider(
    abs_path: str,
    provider_id: str = "",
    model: str = "",
    ms_model: str = "",
    prompt: str = "",
) -> dict[str, Any]:
    text, resolved_model = await caption_image_with_provider(
        abs_path,
        asset_classification_prompt(prompt),
        provider_id or provider_store.get_primary_provider_id(),
        model,
        ms_model,
    )
    classification = parse_asset_classification_text(text)
    classification["model"] = resolved_model
    classification["provider"] = provider_id or provider_store.get_primary_provider_id()
    return classification


async def classify_asset_image_best_effort(
    abs_path: str,
    provider_id: str = "",
    model: str = "",
    ms_model: str = "",
    prompt: str = "",
) -> dict[str, Any] | None:
    try:
        return await classify_image_with_provider(abs_path, provider_id, model, ms_model, prompt)
    except Exception as exc:
        print(f"素材智能分类失败: {exc}")
        return None
