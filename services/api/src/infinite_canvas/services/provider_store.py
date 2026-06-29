"""API provider storage, normalization, and public views — legacy parity."""

from __future__ import annotations

import json
import os
import re
from threading import Lock
from typing import Any

from fastapi import HTTPException

from infinite_canvas.core.env_file import read_api_env_value
from infinite_canvas.core.database import get_setting, set_setting, use_sqlite_storage
from infinite_canvas.core.paths import api_providers_file, legacy_static_dir, static_runninghub_dir
from infinite_canvas.core.provider_constants import (
    JIMENG_DEFAULT_IMAGE_MODELS,
    JIMENG_DEFAULT_VIDEO_MODELS,
    JIMENG_LEGACY_IMAGE_MODELS,
    JIMENG_LEGACY_VIDEO_MODELS,
    LINGJING_DEFAULT_BASE_URL,
    MODELSCOPE_CHAT_BASE_URL,
    MODELSCOPE_DEFAULT_CHAT_MODELS,
    MODELSCOPE_DEFAULT_IMAGE_MODELS,
    MODELSCOPE_DEFAULT_LORAS,
    MODELSCOPE_DEFAULTS_VERSION,
    PER_MODEL_PROTOCOL_OPTIONS,
    PROVIDER_ID_RE,
    RUNNINGHUB_DEFAULT_APPS,
    RUNNINGHUB_DEFAULT_BASE_URL,
    RUNNINGHUB_DEFAULT_WORKFLOWS,
    RUNNINGHUB_THUMBNAIL_EXTS,
    SUPPORTED_IMAGE_REQUEST_MODES,
    SUPPORTED_PROVIDER_PROTOCOLS,
    VOLCENGINE_DEFAULT_BASE_URL,
    VOLCENGINE_DEFAULT_PROJECT_NAME,
    VOLCENGINE_DEFAULT_REGION,
)
from infinite_canvas.core.runtime_config import MODELSCOPE_API_KEY, MODELSCOPE_CHAT_MODELS
from infinite_canvas.core.websocket import now_ms

GLOBAL_CONFIG_LOCK = Lock()
STATIC_RUNNINGHUB_API_PROVIDERS_FILE = static_runninghub_dir() / "api_providers.json"
STATIC_RUNNINGHUB_THUMBNAIL_DIR = static_runninghub_dir() / "thumbnails"
STATIC_RUNNINGHUB_DIR = static_runninghub_dir()


def provider_key_env(provider_id: str) -> str:
    if provider_id == "comfly":
        return "COMFLY_API_KEY"
    if provider_id == "modelscope":
        return "MODELSCOPE_API_KEY"
    if provider_id == "runninghub":
        return "RUNNINGHUB_API_KEY"
    if provider_id == "volcengine":
        return "ARK_API_KEY"
    return f"API_PROVIDER_{re.sub(r'[^A-Za-z0-9]', '_', provider_id).upper()}_KEY"


def runninghub_wallet_key_env() -> str:
    return "RUNNINGHUB_WALLET_API_KEY"


def volcengine_access_key_env() -> str:
    return "VOLCENGINE_ACCESS_KEY_ID"


def volcengine_secret_key_env() -> str:
    return "VOLCENGINE_SECRET_ACCESS_KEY"


def mask_secret(value: str) -> str:
    if not value:
        return ""
    tail = value[-4:] if len(value) > 4 else value
    return f"••••••••{tail}"


def strip_auth_scheme(value: str, scheme: str = "Bearer") -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    pattern = rf"^{re.escape(scheme)}\s+"
    return re.sub(pattern, "", text, flags=re.I).strip()


def bearer_auth_value(value: str) -> str:
    token = strip_auth_scheme(value, "Bearer")
    return f"Bearer {token}" if token else ""


def provider_env_key_value(provider_id: str) -> str:
    provider_id = str(provider_id or "").strip().lower()
    env_key = provider_key_env(provider_id)
    key = os.getenv(env_key, "") or read_api_env_value(env_key)
    if key:
        return key
    if provider_id == "modelscope":
        return MODELSCOPE_API_KEY or ""
    return ""


def runninghub_wallet_key_value() -> str:
    env_key = runninghub_wallet_key_env()
    return os.getenv(env_key, "") or read_api_env_value(env_key)


def volcengine_access_key_value() -> str:
    env_key = volcengine_access_key_env()
    return os.getenv(env_key, "") or read_api_env_value(env_key)


def volcengine_secret_key_value() -> str:
    env_key = volcengine_secret_key_env()
    return os.getenv(env_key, "") or read_api_env_value(env_key)


def volcengine_provider_api_key(explicit_key: str = "") -> str:
    explicit_key = str(explicit_key or "").strip()
    if explicit_key:
        return explicit_key
    return provider_env_key_value("volcengine")


def model_list_from_values(values: list[str] | None) -> list[str]:
    deduped: list[str] = []
    for value in values or []:
        item = str(value or "").strip()
        if item and item not in deduped:
            if len(item) > 240 or any(ord(ch) < 32 or ord(ch) == 127 for ch in item):
                raise HTTPException(status_code=400, detail=f"模型名称不合法：{item}")
            deduped.append(item)
    return deduped


def normalize_ms_loras(values: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in values or []:
        if not isinstance(raw, dict):
            continue
        lora_id = str(raw.get("id") or "").strip()
        if not lora_id:
            continue
        target_model = str(raw.get("target_model") or raw.get("model") or "").strip()
        if not target_model:
            continue
        key = (target_model, lora_id)
        if key in seen:
            continue
        seen.add(key)
        try:
            strength = float(raw.get("strength", raw.get("default_strength", 0.8)))
        except Exception:
            strength = 0.8
        strength = max(0.0, min(2.0, strength))
        name = re.sub(r"\s+", " ", str(raw.get("name") or "").strip())[:80]
        normalized.append(
            {
                "id": lora_id[:180],
                "name": name or lora_id,
                "target_model": target_model[:180],
                "strength": strength,
                "enabled": bool(raw.get("enabled", True)),
                "note": str(raw.get("note") or "").strip()[:300],
            }
        )
    return normalized


def normalize_runninghub_entry(raw: dict[str, Any] | None, kind: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    raw_id = raw.get("appId") if kind == "app" else raw.get("workflowId")
    entry_id = str(raw_id or raw.get("id") or "").strip()
    match = re.search(r"/run/(ai-app|workflow)/([0-9A-Za-z_-]+)", entry_id)
    if match:
        entry_id = match.group(2)
    if not entry_id:
        return None
    title = re.sub(r"\s+", " ", str(raw.get("title") or raw.get("name") or "").strip())[:80]
    note = str(raw.get("note") or raw.get("description") or "").strip()[:500]
    thumb = str(raw.get("thumbnail") or "").strip()
    if len(thumb) > 1500000:
        thumb = ""
    entry: dict[str, Any] = {
        "id": entry_id[:80],
        "title": title or (f"AI 应用 {entry_id[-6:]}" if kind == "app" else f"工作流 {entry_id[-6:]}"),
        "note": note,
        "thumbnail": thumb,
        "enabled": bool(raw.get("enabled", True)),
    }
    if raw.get("hidden") is True:
        entry["hidden"] = True
    fields = raw.get("fields")
    if isinstance(fields, list):
        entry["fields"] = [f for f in fields if isinstance(f, dict)]
    if kind == "workflow":
        mode = str(raw.get("optionalImageMode") or raw.get("optional_image_mode") or "prune-workflow").strip()
        entry["optionalImageMode"] = mode or "prune-workflow"
        workflow_json = raw.get("workflowJson") or raw.get("workflow_json")
        if isinstance(workflow_json, dict):
            entry["workflowJson"] = workflow_json
    raw_payload = raw.get("raw")
    if isinstance(raw_payload, dict):
        entry["raw"] = raw_payload
    try:
        updated_at = int(raw.get("updatedAt") or raw.get("updated_at") or 0)
        if updated_at > 0:
            entry["updatedAt"] = updated_at
    except Exception:
        pass
    if kind == "app":
        entry["appId"] = entry["id"]
    else:
        entry["workflowId"] = entry["id"]
    return entry


def normalize_runninghub_entries(values: list[dict[str, Any]] | None, kind: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in values or []:
        entry = normalize_runninghub_entry(raw, kind)
        if not entry or entry["id"] in seen:
            continue
        seen.add(entry["id"])
        normalized.append(entry)
    return normalized


def runninghub_entry_id(entry: dict[str, Any] | None, kind: str) -> str:
    if not isinstance(entry, dict):
        return ""
    raw_id = entry.get("workflowId") if kind == "workflow" else entry.get("appId")
    return str(raw_id or entry.get("id") or "").strip()


def static_runninghub_thumbnail_url(entry_id: str, kind: str) -> str:
    entry_id = re.sub(r"[^0-9A-Za-z_-]", "", str(entry_id or "").strip())
    kind_prefix = "workflow" if kind == "workflow" else "app"
    if not entry_id:
        return ""
    candidates: list[tuple[Any, str]] = []
    for name in (f"{kind_prefix}-{entry_id}", entry_id):
        for ext in RUNNINGHUB_THUMBNAIL_EXTS:
            candidates.append((STATIC_RUNNINGHUB_THUMBNAIL_DIR, f"{name}{ext}"))
            candidates.append((STATIC_RUNNINGHUB_DIR, f"{name}{ext}"))
    static_root = STATIC_RUNNINGHUB_DIR.resolve()
    legacy_static = legacy_static_dir().resolve()
    for root, filename in candidates:
        path = (root / filename).resolve()
        if not str(path).startswith(str(static_root) + os.sep):
            continue
        if path.is_file():
            rel = path.relative_to(legacy_static).as_posix()
            return f"/static/{rel}?v={int(path.stat().st_mtime)}"
    return ""


def apply_runninghub_system_thumbnails(entries: list[dict[str, Any]] | None, kind: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for entry in normalize_runninghub_entries(entries or [], kind):
        if not entry.get("thumbnail"):
            thumb = static_runninghub_thumbnail_url(runninghub_entry_id(entry, kind), kind)
            if thumb:
                entry["thumbnail"] = thumb
        result.append(entry)
    return result


def merge_runninghub_entry_overlay(system_entry: dict[str, Any], user_entry: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(system_entry, dict):
        return user_entry
    if not isinstance(user_entry, dict):
        return system_entry
    merged = {**system_entry, **user_entry}
    if not merged.get("thumbnail") and system_entry.get("thumbnail"):
        merged["thumbnail"] = system_entry.get("thumbnail")
    return merged


def merge_runninghub_system_entries(
    system_entries: list[dict[str, Any]] | None,
    user_entries: list[dict[str, Any]] | None,
    kind: str,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    index: dict[str, int] = {}
    hidden_ids: set[str] = set()
    for entry in apply_runninghub_system_thumbnails(system_entries or [], kind):
        entry_id = runninghub_entry_id(entry, kind)
        if not entry_id:
            continue
        index[entry_id] = len(merged)
        merged.append(entry)
    for entry in apply_runninghub_system_thumbnails(user_entries or [], kind):
        entry_id = runninghub_entry_id(entry, kind)
        if not entry_id:
            continue
        if entry.get("hidden") is True:
            hidden_ids.add(entry_id)
            if entry_id in index:
                merged.pop(index[entry_id])
                index = {runninghub_entry_id(item, kind): idx for idx, item in enumerate(merged)}
            continue
        if entry_id in index:
            merged[index[entry_id]] = merge_runninghub_entry_overlay(merged[index[entry_id]], entry)
        else:
            index[entry_id] = len(merged)
            merged.append(entry)
    return [entry for entry in merged if runninghub_entry_id(entry, kind) not in hidden_ids]


def normalize_endpoint_override(value: str, label: str) -> str:
    endpoint = str(value or "").strip()
    if not endpoint:
        return ""
    if len(endpoint) > 300 or re.search(r"\s", endpoint):
        raise HTTPException(status_code=400, detail=f"{label} 不合法，请填写类似 /v1/images/edits 的路径")
    if re.match(r"^https?://", endpoint, re.I):
        return endpoint.rstrip("/")
    if not endpoint.startswith("/"):
        raise HTTPException(status_code=400, detail=f"{label} 需要以 /v1/... 开头，或填写完整 http(s) 地址")
    return endpoint


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


def normalize_model_protocols(value: dict[str, str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(value, dict):
        for raw_name, raw_proto in value.items():
            name = str(raw_name or "").strip()
            proto = str(raw_proto or "").strip().lower()
            if name and proto in PER_MODEL_PROTOCOL_OPTIONS:
                out[name] = proto
    return out


def provider_protocol(provider: dict[str, Any] | None) -> str:
    return str((provider or {}).get("protocol") or "openai").strip().lower()


def is_jimeng_provider(provider: dict[str, Any] | None) -> bool:
    return provider_protocol(provider) == "jimeng" or str((provider or {}).get("id") or "").strip().lower() == "jimeng"


def default_api_providers() -> list[dict[str, Any]]:
    return [
        {
            "id": "modelscope",
            "name": "ModelScope",
            "base_url": MODELSCOPE_CHAT_BASE_URL,
            "protocol": "openai",
            "image_request_mode": "openai",
            "image_generation_endpoint": "",
            "image_edit_endpoint": "",
            "enabled": True,
            "primary": False,
            "image_models": MODELSCOPE_DEFAULT_IMAGE_MODELS,
            "chat_models": MODELSCOPE_CHAT_MODELS,
            "video_models": [],
            "ms_loras": MODELSCOPE_DEFAULT_LORAS,
            "ms_defaults_version": MODELSCOPE_DEFAULTS_VERSION,
        },
        {
            "id": "runninghub",
            "name": "RunningHub",
            "base_url": RUNNINGHUB_DEFAULT_BASE_URL,
            "protocol": "runninghub",
            "image_request_mode": "openai",
            "image_generation_endpoint": "",
            "image_edit_endpoint": "",
            "enabled": True,
            "primary": False,
            "image_models": [],
            "chat_models": [],
            "video_models": [],
            "ms_loras": [],
            "ms_defaults_version": 0,
            "rh_apps": RUNNINGHUB_DEFAULT_APPS,
            "rh_workflows": RUNNINGHUB_DEFAULT_WORKFLOWS,
        },
        {
            "id": "volcengine",
            "name": "火山引擎",
            "base_url": VOLCENGINE_DEFAULT_BASE_URL,
            "protocol": "volcengine",
            "image_request_mode": "openai",
            "image_generation_endpoint": "",
            "image_edit_endpoint": "",
            "enabled": True,
            "primary": False,
            "image_models": [],
            "chat_models": [],
            "video_models": [],
            "ms_loras": [],
            "ms_defaults_version": 0,
            "volcengine_project_name": VOLCENGINE_DEFAULT_PROJECT_NAME,
            "volcengine_region": VOLCENGINE_DEFAULT_REGION,
        },
        {
            "id": "lingjing",
            "name": "灵境API",
            "base_url": LINGJING_DEFAULT_BASE_URL,
            "protocol": "openai",
            "image_request_mode": "openai",
            "image_generation_endpoint": "",
            "image_edit_endpoint": "",
            "enabled": True,
            "primary": False,
            "image_models": ["gpt-image-2", "gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview"],
            "chat_models": ["gpt-5.5"],
            "video_models": ["veo3.1-fast"],
            "model_protocols": {
                "gemini-3.1-flash-image-preview": "gemini",
                "gemini-3-pro-image-preview": "gemini",
            },
            "ms_loras": [],
            "ms_defaults_version": 0,
        },
    ]


def load_static_runninghub_provider() -> dict[str, Any] | None:
    if not STATIC_RUNNINGHUB_API_PROVIDERS_FILE.is_file():
        return None
    try:
        raw = json.loads(STATIC_RUNNINGHUB_API_PROVIDERS_FILE.read_text(encoding="utf-8"))
        candidates = raw if isinstance(raw, list) else raw.get("providers") if isinstance(raw, dict) else []
        if isinstance(raw, dict) and raw.get("id") == "runninghub":
            candidates = [raw]
        for item in candidates or []:
            if isinstance(item, dict) and str(item.get("id") or "").strip().lower() == "runninghub":
                provider = normalize_provider(item)
                provider["rh_apps"] = apply_runninghub_system_thumbnails(provider.get("rh_apps") or [], "app")
                provider["rh_workflows"] = apply_runninghub_system_thumbnails(
                    provider.get("rh_workflows") or [], "workflow"
                )
                return provider
    except Exception as exc:
        print(f"加载 static RunningHub 配置失败: {exc}")
    return None


def merge_default_api_providers(providers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = [dict(item) for item in providers]
    ms_default = next((d for d in default_api_providers() if d["id"] == "modelscope"), None)
    if ms_default:
        current = next((item for item in merged if item.get("id") == "modelscope"), None)
        if not current:
            merged.append(ms_default)
        else:
            if not current.get("base_url"):
                current["base_url"] = ms_default["base_url"]
            seeded_version = int(current.get("ms_defaults_version") or 0)
            if seeded_version < MODELSCOPE_DEFAULTS_VERSION:
                current["image_models"] = model_list_from_values(
                    [*MODELSCOPE_DEFAULT_IMAGE_MODELS, *(current.get("image_models") or [])]
                )
                current["chat_models"] = model_list_from_values(
                    [*MODELSCOPE_DEFAULT_CHAT_MODELS, *(current.get("chat_models") or [])]
                )
                current["ms_loras"] = normalize_ms_loras(
                    [*MODELSCOPE_DEFAULT_LORAS, *(current.get("ms_loras") or [])]
                )
                current["ms_defaults_version"] = MODELSCOPE_DEFAULTS_VERSION
    rh_default = load_static_runninghub_provider() or next(
        (d for d in default_api_providers() if d["id"] == "runninghub"), None
    )
    if rh_default:
        current = next((item for item in merged if item.get("id") == "runninghub"), None)
        if not current:
            merged.append(rh_default)
        else:
            if not current.get("base_url"):
                current["base_url"] = rh_default["base_url"]
            if not current.get("protocol") or current.get("protocol") == "openai":
                current["protocol"] = "runninghub"
            current["image_models"] = model_list_from_values(current.get("image_models") or [])
            current["chat_models"] = model_list_from_values(current.get("chat_models") or [])
            current["video_models"] = model_list_from_values(current.get("video_models") or [])
            current["rh_apps"] = merge_runninghub_system_entries(
                rh_default.get("rh_apps") or [], current.get("rh_apps") or [], "app"
            )
            current["rh_workflows"] = merge_runninghub_system_entries(
                rh_default.get("rh_workflows") or [], current.get("rh_workflows") or [], "workflow"
            )
    volc_default = next((d for d in default_api_providers() if d["id"] == "volcengine"), None)
    if volc_default:
        current = next((item for item in merged if item.get("id") == "volcengine"), None)
        legacy = next(
            (
                item
                for item in merged
                if item.get("id") != "volcengine" and str(item.get("protocol") or "").lower() == "volcengine"
            ),
            None,
        )
        if not current:
            if legacy:
                merged.append(
                    {
                        **volc_default,
                        "base_url": legacy.get("base_url") or volc_default["base_url"],
                        "image_models": model_list_from_values(legacy.get("image_models") or [])
                        or model_list_from_values(volc_default.get("image_models") or []),
                        "chat_models": model_list_from_values(legacy.get("chat_models") or []),
                        "video_models": model_list_from_values(legacy.get("video_models") or []),
                    }
                )
            else:
                merged.append(volc_default)
        else:
            if not current.get("base_url"):
                current["base_url"] = volc_default["base_url"]
            current["protocol"] = "volcengine"
            current["volcengine_project_name"] = (
                str(current.get("volcengine_project_name") or VOLCENGINE_DEFAULT_PROJECT_NAME).strip()
                or VOLCENGINE_DEFAULT_PROJECT_NAME
            )
            current["volcengine_region"] = (
                str(current.get("volcengine_region") or VOLCENGINE_DEFAULT_REGION).strip()
                or VOLCENGINE_DEFAULT_REGION
            )
    lingjing_default = next((d for d in default_api_providers() if d["id"] == "lingjing"), None)
    if lingjing_default:
        current = next((item for item in merged if item.get("id") == "lingjing"), None)
        if not current:
            merged.append(lingjing_default)
        else:
            if not current.get("base_url"):
                current["base_url"] = lingjing_default["base_url"]
            if not current.get("protocol"):
                current["protocol"] = "openai"
            current["image_request_mode"] = normalize_image_request_mode(current.get("image_request_mode"))
            current["image_models"] = model_list_from_values(
                [*(current.get("image_models") or []), *(lingjing_default.get("image_models") or [])]
            )
            current["chat_models"] = model_list_from_values(
                [*(current.get("chat_models") or []), *(lingjing_default.get("chat_models") or [])]
            )
            current["video_models"] = model_list_from_values(
                [*(current.get("video_models") or []), *(lingjing_default.get("video_models") or [])]
            )
            protocols = normalize_model_protocols(current.get("model_protocols"))
            protocols.update(normalize_model_protocols(lingjing_default.get("model_protocols")))
            current["model_protocols"] = protocols
    for current in merged:
        if not is_jimeng_provider(current):
            continue
        current["protocol"] = "jimeng"
        current["base_url"] = ""
        current["image_models"] = model_list_from_values(
            [
                *[
                    item
                    for item in (current.get("image_models") or [])
                    if str(item or "").strip() not in JIMENG_LEGACY_IMAGE_MODELS
                ],
                *JIMENG_DEFAULT_IMAGE_MODELS,
            ]
        )
        current["video_models"] = model_list_from_values(
            [
                *[
                    item
                    for item in (current.get("video_models") or [])
                    if str(item or "").strip() not in JIMENG_LEGACY_VIDEO_MODELS
                ],
                *JIMENG_DEFAULT_VIDEO_MODELS,
            ]
        )
    return merged


def normalize_provider(item: dict[str, Any]) -> dict[str, Any]:
    provider_id = str(item.get("id") or "").strip().lower()
    if not PROVIDER_ID_RE.fullmatch(provider_id):
        raise HTTPException(status_code=400, detail=f"API 平台 ID 不合法：{provider_id or '(empty)'}")
    name = re.sub(r"\s+", " ", str(item.get("name") or provider_id).strip())[:60] or provider_id
    base_url = str(item.get("base_url") or "").strip().rstrip("/")
    if base_url and not re.match(r"^https?://", base_url):
        raise HTTPException(status_code=400, detail=f"{name} 的 Base URL 需要以 http:// 或 https:// 开头")
    protocol = str(item.get("protocol") or "openai").strip().lower()
    if protocol not in SUPPORTED_PROVIDER_PROTOCOLS:
        protocol = "openai"
    image_request_mode = detect_image_request_mode(base_url, item.get("image_models") or []) or normalize_image_request_mode(
        str(item.get("image_request_mode") or "")
    )
    image_generation_endpoint = normalize_endpoint_override(
        str(item.get("image_generation_endpoint") or ""), "文生图端口"
    )
    image_edit_endpoint = normalize_endpoint_override(str(item.get("image_edit_endpoint") or ""), "图生图/编辑端口")
    volc_project = re.sub(r"\s+", " ", str(item.get("volcengine_project_name") or "").strip())[:80]
    volc_region = re.sub(r"\s+", " ", str(item.get("volcengine_region") or "").strip())[:40]
    if provider_id == "volcengine":
        protocol = "volcengine"
        base_url = base_url or VOLCENGINE_DEFAULT_BASE_URL
        volc_project = volc_project or VOLCENGINE_DEFAULT_PROJECT_NAME
        volc_region = volc_region or VOLCENGINE_DEFAULT_REGION
    if provider_id == "jimeng":
        protocol = "jimeng"
        base_url = ""
    if provider_id == "runninghub":
        protocol = "runninghub"
        base_url = base_url or RUNNINGHUB_DEFAULT_BASE_URL
    return {
        "id": provider_id,
        "name": name,
        "base_url": base_url,
        "protocol": protocol,
        "image_request_mode": image_request_mode,
        "image_generation_endpoint": image_generation_endpoint,
        "image_edit_endpoint": image_edit_endpoint,
        "enabled": bool(item.get("enabled", True)),
        "primary": bool(item.get("primary", False)),
        "image_models": model_list_from_values(item.get("image_models") or []),
        "chat_models": model_list_from_values(item.get("chat_models") or []),
        "video_models": model_list_from_values(item.get("video_models") or []),
        "model_protocols": normalize_model_protocols(item.get("model_protocols")),
        "ms_loras": normalize_ms_loras(item.get("ms_loras") or []),
        "ms_defaults_version": int(item.get("ms_defaults_version") or 0),
        "rh_apps": normalize_runninghub_entries(item.get("rh_apps") or [], "app"),
        "rh_workflows": normalize_runninghub_entries(item.get("rh_workflows") or [], "workflow"),
        "volcengine_project_name": volc_project,
        "volcengine_region": volc_region,
    }


def preserve_runninghub_hidden_overrides(provider: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(provider, dict) or provider.get("id") != "runninghub":
        return provider
    static_provider = load_static_runninghub_provider()
    if not static_provider:
        return provider
    provider = dict(provider)
    for list_key, kind in (("rh_apps", "app"), ("rh_workflows", "workflow")):
        current = normalize_runninghub_entries(provider.get(list_key) or [], kind)
        current_ids = {runninghub_entry_id(item, kind) for item in current}
        for static_entry in static_provider.get(list_key) or []:
            entry_id = runninghub_entry_id(static_entry, kind)
            if entry_id and entry_id not in current_ids:
                tombstone = normalize_runninghub_entry({**static_entry, "enabled": False, "hidden": True}, kind)
                if tombstone:
                    current.append(tombstone)
        provider[list_key] = current
    return provider


def load_api_providers() -> list[dict[str, Any]]:
    defaults = default_api_providers()
    if use_sqlite_storage():
        stored = get_setting("api_providers")
        if isinstance(stored, list) and stored:
            providers = [normalize_provider(item) for item in stored if isinstance(item, dict)]
            return merge_default_api_providers(providers or defaults)
        return merge_default_api_providers(defaults)
    path = api_providers_file()
    if not path.is_file():
        return merge_default_api_providers(defaults)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        providers = [normalize_provider(item) for item in raw if isinstance(item, dict)]
        return merge_default_api_providers(providers or defaults)
    except Exception as exc:
        print(f"加载 API 平台配置失败: {exc}")
        return defaults


def save_api_providers(providers: list[dict[str, Any]]) -> None:
    if use_sqlite_storage():
        with GLOBAL_CONFIG_LOCK:
            set_setting("api_providers", providers, updated_at=now_ms())
        return
    path = api_providers_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with GLOBAL_CONFIG_LOCK:
        path.write_text(json.dumps(providers, ensure_ascii=False, indent=2), encoding="utf-8")


def public_provider(provider: dict[str, Any]) -> dict[str, Any]:
    key = provider_env_key_value(provider["id"])
    item = {
        **provider,
        "has_key": bool(key),
        "key_preview": mask_secret(key),
        "key_env": provider_key_env(provider["id"]),
    }
    if provider.get("id") == "runninghub":
        wallet_key = runninghub_wallet_key_value()
        item.update(
            {
                "has_wallet_key": bool(wallet_key),
                "wallet_key_preview": mask_secret(wallet_key),
                "wallet_key_env": runninghub_wallet_key_env(),
            }
        )
    if provider.get("id") == "volcengine":
        ak = volcengine_access_key_value()
        sk = volcengine_secret_key_value()
        item.update(
            {
                "has_volcengine_access_key": bool(ak),
                "volcengine_access_key_preview": mask_secret(ak),
                "volcengine_access_key_env": volcengine_access_key_env(),
                "has_volcengine_secret_key": bool(sk),
                "volcengine_secret_key_preview": mask_secret(sk),
                "volcengine_secret_key_env": volcengine_secret_key_env(),
                "volcengine_project_name": provider.get("volcengine_project_name") or VOLCENGINE_DEFAULT_PROJECT_NAME,
                "volcengine_region": provider.get("volcengine_region") or VOLCENGINE_DEFAULT_REGION,
            }
        )
    return item


def public_api_providers() -> list[dict[str, Any]]:
    return [public_provider(p) for p in load_api_providers()]


def get_primary_provider_id(providers: list[dict[str, Any]] | None = None) -> str:
    providers = providers if providers is not None else load_api_providers()
    primary = next((p for p in providers if p.get("primary") and p.get("enabled", True)), None)
    if primary:
        return primary["id"]
    non_ms = next((p for p in providers if p["id"] != "modelscope" and p.get("enabled", True)), None)
    if non_ms:
        return non_ms["id"]
    return providers[0]["id"] if providers else "modelscope"


def get_api_provider(provider_id: str = "comfly") -> dict[str, Any]:
    providers = load_api_providers()
    target = (provider_id or "").strip().lower()
    if not target or not any(p["id"] == target for p in providers):
        target = get_primary_provider_id(providers)
    provider = next((p for p in providers if p["id"] == target), None)
    if not provider:
        raise HTTPException(status_code=400, detail=f"未找到 API 平台：{target}")
    if not provider.get("enabled", True):
        raise HTTPException(status_code=400, detail=f"API 平台已禁用：{provider.get('name') or target}")
    return provider


def get_api_provider_exact(provider_id: str) -> dict[str, Any]:
    providers = load_api_providers()
    target = (provider_id or "").strip().lower()
    provider = next((p for p in providers if p["id"] == target), None)
    if not provider:
        raise HTTPException(
            status_code=400,
            detail=f"未找到 API 平台：{target or '(empty)'}。新增平台未保存时请使用当前表单拉取模型。",
        )
    if not provider.get("enabled", True):
        raise HTTPException(status_code=400, detail=f"API 平台已禁用：{provider.get('name') or target}")
    return provider


def modelscope_api_key(explicit_key: str = "") -> str:
    return (
        strip_auth_scheme(explicit_key, "Bearer")
        or strip_auth_scheme(provider_env_key_value("modelscope"), "Bearer")
        or strip_auth_scheme(MODELSCOPE_API_KEY, "Bearer")
    )
