"""ModelScope image API helpers — legacy parity."""

from __future__ import annotations

import re

from fastapi import HTTPException

from infinite_canvas.core.provider_constants import MODELSCOPE_CHAT_BASE_URL
from infinite_canvas.core.runtime_config import MODELSCOPE_API_KEY
from infinite_canvas.services import asset_ai, provider_store


def modelscope_image_api_root() -> str:
    return MODELSCOPE_CHAT_BASE_URL.rstrip("/")


def modelscope_size(value: str, fallback: str = "1024x1024") -> str:
    size = str(value or fallback).strip().lower().replace("*", "x")
    if re.fullmatch(r"\d{2,5}x\d{2,5}", size):
        return size
    raise HTTPException(
        status_code=400,
        detail=f"ModelScope size 格式不正确：{value or fallback}，应为 WxH，例如 1024x1024",
    )


def modelscope_image_url(value: str, max_size: int = 1536) -> str:
    if not value:
        return value
    if isinstance(value, str) and (value.startswith("/output/") or value.startswith("/assets/")):
        from infinite_canvas.services.media_references import reference_to_data_url

        return reference_to_data_url({"url": value}, max_size=max_size)
    return value


def modelscope_auth_headers(api_key: str = "", async_mode: bool = True) -> dict[str, str]:
    clean_token = provider_store.modelscope_api_key(api_key)
    if not clean_token:
        raise HTTPException(status_code=400, detail="未提供 ModelScope API Key")
    headers = {
        "Authorization": provider_store.bearer_auth_value(clean_token),
        "Content-Type": "application/json",
    }
    if async_mode:
        headers["X-ModelScope-Async-Mode"] = "true"
    return headers


def resolve_modelscope_token(explicit_key: str = "") -> str:
    token = provider_store.modelscope_api_key(explicit_key)
    if not token:
        raise HTTPException(
            status_code=400,
            detail="未配置 ModelScope API Key，请在 API 设置中填写，或重新保存 ModelScope Token。",
        )
    return token
