"""Provider, config, and model endpoints."""

from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException

from infinite_canvas.core.env_file import update_env_values
from infinite_canvas.core.paths import global_config_file
from infinite_canvas.core.runtime_config import (
    AI_API_KEY,
    AI_BASE_URL,
    CHAT_MODEL,
    CHAT_MODELS,
    COMFYUI_INSTANCES,
    IMAGE_MODEL,
    IMAGE_MODELS,
    MODELSCOPE_CHAT_MODELS,
    VIDEO_MODELS,
    reload_env_globals,
)
from infinite_canvas.schemas.provider import ApiProviderPayload, TestConnectionPayload
from infinite_canvas.services import provider_probe, provider_store

router = APIRouter(tags=["providers"])


@router.get("/api/config")
async def ai_config():
    preferred_chat_model = next((m for m in CHAT_MODELS if m == "gpt-5.5"), CHAT_MODELS[0] if CHAT_MODELS else CHAT_MODEL)
    providers = provider_store.public_api_providers()
    return {
        "base_url": AI_BASE_URL,
        "chat_model": preferred_chat_model,
        "image_model": IMAGE_MODEL,
        "chat_models": CHAT_MODELS,
        "image_models": IMAGE_MODELS,
        "video_models": VIDEO_MODELS,
        "comfy_instances": COMFYUI_INSTANCES,
        "api_providers": providers,
        "has_api_key": bool(AI_API_KEY),
        "ms_chat_models": MODELSCOPE_CHAT_MODELS,
        "has_ms_key": bool(provider_store.modelscope_api_key()),
    }


@router.get("/api/models")
async def ai_models():
    return {"chat_models": CHAT_MODELS, "image_models": IMAGE_MODELS, "video_models": VIDEO_MODELS}


@router.get("/api/providers")
async def api_providers():
    return {"providers": provider_store.public_api_providers()}


@router.put("/api/providers")
async def save_providers(payload: list[ApiProviderPayload]):
    providers: list[dict] = []
    env_updates: dict[str, str] = {}
    raw_primary_flags = [bool(getattr(item, "primary", False)) for item in payload]
    for item in payload:
        provider = provider_store.normalize_provider(item.model_dump(exclude={"api_key"}))
        if provider["id"] == "runninghub":
            provider = provider_store.preserve_runninghub_hidden_overrides(provider)
        if any(existing["id"] == provider["id"] for existing in providers):
            raise HTTPException(status_code=400, detail=f"API 平台 ID 重复：{provider['id']}")
        providers.append(provider)
        key_env = provider_store.provider_key_env(provider["id"])
        if item.clear_key:
            env_updates[key_env] = ""
        elif item.api_key is not None and item.api_key.strip():
            env_updates[key_env] = item.api_key.strip()
        if provider["id"] == "runninghub":
            wallet_env = provider_store.runninghub_wallet_key_env()
            if item.clear_wallet_key:
                env_updates[wallet_env] = ""
            elif item.wallet_api_key is not None and item.wallet_api_key.strip():
                env_updates[wallet_env] = item.wallet_api_key.strip()
        if provider["id"] == "volcengine":
            ak_env = provider_store.volcengine_access_key_env()
            sk_env = provider_store.volcengine_secret_key_env()
            if item.clear_volcengine_access_key_id:
                env_updates[ak_env] = ""
            elif item.volcengine_access_key_id is not None and item.volcengine_access_key_id.strip():
                env_updates[ak_env] = item.volcengine_access_key_id.strip()
            if item.clear_volcengine_secret_access_key:
                env_updates[sk_env] = ""
            elif item.volcengine_secret_access_key is not None and item.volcengine_secret_access_key.strip():
                env_updates[sk_env] = item.volcengine_secret_access_key.strip()
        if provider["id"] == "comfly":
            env_updates["COMFLY_BASE_URL"] = provider["base_url"]
            env_updates["IMAGE_MODELS"] = ",".join(provider["image_models"])
            env_updates["CHAT_MODELS"] = ",".join(provider["chat_models"])
            env_updates["VIDEO_MODELS"] = ",".join(provider.get("video_models") or [])
        if provider["id"] == "modelscope":
            env_updates["MODELSCOPE_CHAT_MODELS"] = ",".join(provider["chat_models"])
        if provider["id"] == "runninghub":
            provider["protocol"] = "runninghub"
        if provider["id"] == "volcengine":
            provider["protocol"] = "volcengine"
    if not providers:
        raise HTTPException(status_code=400, detail="至少保留一个 API 平台")
    primary_indices = [i for i, flag in enumerate(raw_primary_flags) if flag]
    if primary_indices:
        winner = primary_indices[-1]
        for i, p in enumerate(providers):
            p["primary"] = i == winner
    provider_store.save_api_providers(providers)
    if env_updates:
        update_env_values(env_updates)
        reload_env_globals()
    return {"providers": [provider_store.public_provider(p) for p in providers]}


@router.get("/api/config/token")
async def get_global_token():
    saved_token = provider_store.modelscope_api_key()
    if saved_token:
        return {"token": saved_token}
    path = global_config_file()
    if path.is_file():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            return {"token": config.get("modelscope_token", "")}
        except Exception:
            pass
    return {"token": ""}


@router.post("/api/providers/test-connection")
async def test_provider_connection(payload: TestConnectionPayload):
    return await provider_probe.test_provider_connection(payload)


@router.post("/api/providers/probe-async")
async def probe_async_endpoint(payload: TestConnectionPayload):
    return await provider_probe.probe_async_endpoint(payload)


@router.post("/api/providers/fetch-models")
async def fetch_upstream_models_from_payload(payload: TestConnectionPayload):
    protocol = provider_probe.protocol_from_payload(payload)
    api_key = provider_probe.api_key_from_payload(payload, protocol)
    return await provider_probe.fetch_models_from_upstream(
        payload.base_url, api_key, protocol, payload.image_request_mode
    )


@router.get("/api/providers/{provider_id}/fetch-models")
async def fetch_upstream_models(provider_id: str):
    provider = provider_store.get_api_provider_exact(provider_id)
    api_key = os.getenv(provider_store.runninghub_wallet_key_env(), "") if provider["id"] == "runninghub" else ""
    if not api_key:
        api_key = os.getenv(provider_store.provider_key_env(provider["id"]), "")
    if not api_key:
        raise HTTPException(status_code=400, detail=f"{provider.get('name') or provider_id} 未配置 API Key")
    return await provider_probe.fetch_models_from_upstream(
        provider.get("base_url") or "",
        api_key,
        provider_store.provider_protocol(provider),
        provider.get("image_request_mode") or "openai",
    )
