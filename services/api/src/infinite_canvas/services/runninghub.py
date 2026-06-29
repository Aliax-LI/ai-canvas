"""RunningHub integration — legacy main.py parity (~9839-10156, helpers)."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import uuid
from threading import Lock
from typing import Any

import httpx
from fastapi import HTTPException
from PIL import Image

from infinite_canvas.core.media import content_type_for_path, output_path_for, output_url_for
from infinite_canvas.core.output_files import output_file_from_url
from infinite_canvas.core.paths import runninghub_workflow_store_file
from infinite_canvas.core.provider_constants import (
    RUNNINGHUB_DEFAULT_APPS,
    RUNNINGHUB_DEFAULT_BASE_URL,
)
from infinite_canvas.core.websocket import now_ms
from infinite_canvas.schemas.runninghub import (
    RunningHubSubmitRequest,
    RunningHubUploadAssetRequest,
    RunningHubWorkflowConfig,
    RunningHubWorkflowSubmitRequest,
)
from infinite_canvas.services import provider_store

RUNNINGHUB_WORKFLOW_LOCK = Lock()
SEED_UINT32_MAX = 4294967295

_HTTP_TIMEOUT_SHORT = httpx.Timeout(connect=20.0, read=120.0, write=30.0, pool=20.0)
_HTTP_TIMEOUT_SUBMIT = httpx.Timeout(connect=20.0, read=180.0, write=120.0, pool=20.0)
_HTTP_TIMEOUT_WORKFLOW = httpx.Timeout(connect=20.0, read=180.0, write=60.0, pool=20.0)
_HTTP_TIMEOUT_QUERY = httpx.Timeout(connect=20.0, read=240.0, write=30.0, pool=20.0)
_HTTP_TIMEOUT_UPLOAD = httpx.Timeout(connect=20.0, read=240.0, write=240.0, pool=20.0)


def runninghub_provider() -> dict[str, Any]:
    return provider_store.get_api_provider_exact("runninghub")


def runninghub_endpoint_url(provider: dict[str, Any] | None, path: str) -> str:
    base_url = str((provider or {}).get("base_url") or RUNNINGHUB_DEFAULT_BASE_URL).strip().rstrip("/")
    return f"{base_url}{path}"


def runninghub_api_key(provider: dict[str, Any] | None = None, use_wallet: bool = False, prefer_wallet: bool = False) -> str:
    provider = provider or runninghub_provider()
    free_key = str((provider or {}).get("api_key") or "").strip() or provider_store.provider_env_key_value(provider["id"])
    wallet_key = str((provider or {}).get("wallet_api_key") or "").strip() or provider_store.runninghub_wallet_key_value()
    api_key = wallet_key if (use_wallet or prefer_wallet) and wallet_key else free_key
    if not api_key:
        raise HTTPException(status_code=400, detail="未配置 RunningHub API Key，请在 RH 设置中填写。")
    return api_key


def runninghub_app_headers(json_body: bool = True, use_wallet: bool = False) -> dict[str, str]:
    headers = {"Host": "www.runninghub.cn"}
    provider = runninghub_provider()
    if provider:
        free_key = provider_store.provider_env_key_value(provider["id"])
        wallet_key = provider_store.runninghub_wallet_key_value()
        api_key = wallet_key if use_wallet and wallet_key else free_key
        if api_key:
            headers["Authorization"] = provider_store.bearer_auth_value(api_key)
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def rh_is_seed_like_name(*parts: Any) -> bool:
    text = " ".join(str(part or "") for part in parts).lower()
    return any(key in text for key in ("seed", "noise", "随机", "种子", "噪"))


def normalize_seed_uint32(value: Any) -> Any:
    try:
        if isinstance(value, bool):
            return value
        raw = str(value).strip()
        if not raw:
            return value
        num = int(float(raw))
    except Exception:
        return value
    if 0 <= num <= SEED_UINT32_MAX:
        return value
    safe = ((abs(num) - 1) % SEED_UINT32_MAX) + 1
    return str(safe) if isinstance(value, str) else safe


def sanitize_seed_like_workflow_values(value: Any, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if rh_is_seed_like_name(key) and not isinstance(item, (dict, list)):
                result[key] = normalize_seed_uint32(item)
            else:
                result[key] = sanitize_seed_like_workflow_values(item, key)
        return result
    if isinstance(value, list):
        return [sanitize_seed_like_workflow_values(item, parent_key) for item in value]
    if rh_is_seed_like_name(parent_key):
        return normalize_seed_uint32(value)
    return value


def sanitize_runninghub_node_info_list(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        clean = dict(item)
        if rh_is_seed_like_name(clean.get("fieldName"), clean.get("label"), clean.get("note")):
            clean["fieldValue"] = normalize_seed_uint32(clean.get("fieldValue"))
        result.append(clean)
    return result


def runninghub_local_asset_path(url: str) -> str | None:
    from infinite_canvas.core.paths import assets_input_dir, assets_output_dir

    text = str(url or "").strip()
    if not text:
        return None
    if text.startswith("/assets/input/") or text.startswith("/input/"):
        clean = urllib.parse.unquote(text.split("?", 1)[0]).replace("\\", "/")
        rel = clean[len("/assets/input/") :] if clean.startswith("/assets/input/") else clean[len("/input/") :]
        root = assets_input_dir()
    elif text.startswith("/assets/output/"):
        clean = urllib.parse.unquote(text.split("?", 1)[0]).replace("\\", "/")
        rel = clean[len("/assets/output/") :]
        root = assets_output_dir()
    elif text.startswith("/output/") or text.startswith("/assets/"):
        path = output_file_from_url(text)
        return str(path) if path else None
    else:
        return None
    rel = rel.lstrip("/")
    if not rel:
        return None
    path = os.path.abspath(os.path.join(str(root), rel))
    root_abs = os.path.abspath(str(root))
    if os.path.commonpath([root_abs, path]) != root_abs or not os.path.exists(path):
        return None
    return path


def runninghub_output_ext(remote: str, content_type: str = "") -> str:
    tail = str(remote or "").split("?", 1)[0].split("#", 1)[0]
    ext = os.path.splitext(tail)[1].lower().strip(".")
    allowed = {
        "png", "jpg", "jpeg", "webp", "gif", "bmp", "mp4", "webm", "mov", "m4v", "mkv",
        "mp3", "wav", "ogg", "m4a", "flac", "aac",
    }
    if ext in allowed:
        return ext
    ct = str(content_type or "").lower()
    if "mp4" in ct:
        return "mp4"
    if "webm" in ct:
        return "webm"
    if "quicktime" in ct:
        return "mov"
    if "mpeg" in ct:
        return "mp3"
    if "wav" in ct:
        return "wav"
    if "ogg" in ct:
        return "ogg"
    if "webp" in ct:
        return "webp"
    if "jpeg" in ct:
        return "jpg"
    return "png"


def runninghub_extract_outputs(data: Any) -> list[str]:
    arr: list[Any] = []
    if isinstance(data, list):
        arr = data
    elif isinstance(data, dict):
        for key in ("outputs", "results", "files", "data"):
            value = data.get(key)
            if isinstance(value, list):
                arr = value
                break
        if not arr and (data.get("fileUrl") or data.get("url")):
            arr = [data]
    outputs: list[str] = []
    for item in arr:
        if isinstance(item, str):
            outputs.append(item)
        elif isinstance(item, dict):
            url = (
                item.get("fileUrl")
                or item.get("file_url")
                or item.get("url")
                or item.get("downloadUrl")
                or item.get("download_url")
            )
            if isinstance(url, list):
                outputs.extend([str(u) for u in url if u])
            elif url:
                outputs.append(str(url))
    return outputs


async def runninghub_store_remote_output(client: httpx.AsyncClient, remote: str) -> str:
    if not str(remote or "").startswith(("http://", "https://")):
        return remote
    response = await client.get(remote, follow_redirects=True)
    if not response.is_success:
        return remote
    ext = runninghub_output_ext(remote, response.headers.get("content-type", ""))
    filename = f"rh_{uuid.uuid4().hex[:12]}.{ext}"
    path = output_path_for(filename, "output")
    path.write_bytes(response.content)
    return output_url_for(filename, "output")


def runninghub_fail_reason(raw: Any) -> str:
    data = raw.get("data") if isinstance(raw, dict) else None
    values: list[Any] = []
    if isinstance(data, dict):
        values.extend([data.get("failedReason"), data.get("failReason"), data.get("message"), data.get("error")])
    if isinstance(raw, dict):
        values.extend([raw.get("msg"), raw.get("message"), raw.get("error")])
    for value in values:
        if not value:
            continue
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return str(value.get("exception_message") or value.get("message") or json.dumps(value, ensure_ascii=False))
        return str(value)
    return ""


def runninghub_is_workflow_link_value(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )


def runninghub_infer_workflow_field_type(field_name: str, field_value: str) -> str:
    key = f"{field_name or ''} {field_value or ''}".lower()
    if re.search(r"\b(image|img|mask|photo|picture)\b", key) or re.search(
        r"\.(png|jpe?g|webp|gif|bmp)(\?|$)", key, re.I
    ):
        return "IMAGE"
    if re.search(r"\b(video|movie|mp4)\b", key) or re.search(r"\.(mp4|webm|mov|m4v|mkv)(\?|$)", key, re.I):
        return "VIDEO"
    if re.search(r"\b(audio|sound|music|voice)\b", key) or re.search(r"\.(mp3|wav|ogg|m4a|flac|aac)(\?|$)", key, re.I):
        return "AUDIO"
    text = str(field_value or "").strip()
    if text.lower() in {"true", "false"}:
        return "BOOLEAN"
    try:
        if text:
            float(text)
            return "NUMBER"
    except Exception:
        pass
    return "TEXT"


def runninghub_workflow_node_info_list(workflow_json: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(workflow_json, dict):
        return result
    for node_id, node_content in workflow_json.items():
        inputs = node_content.get("inputs") if isinstance(node_content, dict) else None
        if not isinstance(inputs, dict):
            continue
        for field_name, raw_value in inputs.items():
            if runninghub_is_workflow_link_value(raw_value):
                continue
            if isinstance(raw_value, (dict, list)):
                field_value = json.dumps(raw_value, ensure_ascii=False)
            elif raw_value is None:
                field_value = ""
            else:
                field_value = str(raw_value)
            result.append(
                {
                    "nodeId": str(node_id),
                    "fieldName": str(field_name),
                    "fieldValue": field_value,
                    "fieldType": runninghub_infer_workflow_field_type(field_name, field_value),
                    "source": "workflow",
                }
            )
    return result


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


def runninghub_workflow_store_key(workflow_id: str) -> str:
    return str(workflow_id or "").strip()


def load_runninghub_workflow_store() -> dict[str, Any]:
    path = runninghub_workflow_store_file()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_runninghub_workflow_store(store: dict[str, Any]) -> None:
    path = runninghub_workflow_store_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def runninghub_workflow_config_has_payload(cfg: dict[str, Any] | None) -> bool:
    if not isinstance(cfg, dict):
        return False
    return bool(cfg.get("fields") or cfg.get("workflowJson") or cfg.get("raw"))


def runninghub_static_workflow_entry(workflow_id: str) -> dict[str, Any] | None:
    key = runninghub_workflow_store_key(workflow_id)
    if not key:
        return None
    static_provider = provider_store.load_static_runninghub_provider()
    for entry in (static_provider or {}).get("rh_workflows", []) or []:
        if provider_store.runninghub_entry_id(entry, "workflow") == key or runninghub_workflow_store_key(
            entry.get("workflowId") or entry.get("id")
        ) == key:
            return entry
    return None


def runninghub_static_workflow_config(workflow_id: str) -> dict[str, Any] | None:
    entry = runninghub_static_workflow_entry(workflow_id)
    if not isinstance(entry, dict):
        return None
    key = runninghub_workflow_store_key(entry.get("workflowId") or entry.get("id"))
    cfg = {
        "workflowId": key,
        "title": entry.get("title") or key,
        "description": entry.get("note") or entry.get("description") or "",
        "fields": [
            field
            for field in (runninghub_normalize_field(item) for item in (entry.get("fields") or []))
            if not runninghub_is_saved_link_field(field)
        ],
        "workflowJson": entry.get("workflowJson") if isinstance(entry.get("workflowJson"), dict) else {},
        "optionalImageMode": entry.get("optionalImageMode") or "prune-workflow",
        "raw": entry.get("raw") if isinstance(entry.get("raw"), dict) else {},
        "updatedAt": entry.get("updatedAt") or 0,
        "source": "static_template",
    }
    return cfg if runninghub_workflow_config_has_payload(cfg) else None


def runninghub_normalize_field(raw: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    fallback = fallback or {}
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    elif hasattr(raw, "dict"):
        raw = raw.dict()
    if not isinstance(raw, dict):
        raw = {}
    options = raw.get("options", fallback.get("options", []))
    if isinstance(options, str):
        options = [item.strip() for item in re.split(r"[\r\n,]+", options) if item.strip()]
    elif isinstance(options, list):
        options = [str(item).strip() for item in options if str(item).strip()]
    else:
        options = []
    field_id = str(
        raw.get("id") or raw.get("fieldId") or raw.get("key") or raw.get("nodeId") or fallback.get("id") or ""
    ).strip()
    node_id = str(raw.get("nodeId") or fallback.get("nodeId") or raw.get("node_id") or "").strip()
    field_name = str(
        raw.get("fieldName") or raw.get("inputName") or raw.get("name") or fallback.get("fieldName") or ""
    ).strip()
    field_value = raw.get("fieldValue")
    if field_value is None:
        field_value = raw.get("defaultValue")
    if field_value is None:
        field_value = raw.get("value")
    if field_value is None:
        field_value = fallback.get("fieldValue", "")
    if isinstance(field_value, (dict, list)):
        field_value = json.dumps(field_value, ensure_ascii=False)
    elif field_value is None:
        field_value = ""
    else:
        field_value = str(field_value)
    return {
        "id": field_id or f"{node_id}::{field_name}",
        "nodeId": node_id,
        "fieldName": field_name,
        "fieldValue": field_value,
        "fieldType": str(raw.get("fieldType") or fallback.get("fieldType") or "TEXT"),
        "label": str(raw.get("label") or raw.get("title") or field_name or fallback.get("label") or ""),
        "enabled": bool(raw.get("enabled", fallback.get("enabled", True))),
        "sourceFromUpstream": bool(raw.get("sourceFromUpstream", fallback.get("sourceFromUpstream", True))),
        "group": str(raw.get("group") or fallback.get("group") or ""),
        "note": str(raw.get("note") or fallback.get("note") or ""),
        "options": options,
        "random_enabled": bool(raw.get("random_enabled", fallback.get("random_enabled", False))),
        "min": raw.get("min", fallback.get("min", "")),
        "max": raw.get("max", fallback.get("max", "")),
        "step": raw.get("step", fallback.get("step", "")),
        "imageOrder": int(raw.get("imageOrder") or raw.get("image_order") or fallback.get("imageOrder") or 0),
        "required": bool(raw.get("required", fallback.get("required", False))),
    }


def runninghub_is_saved_link_field(field: dict[str, Any] | None) -> bool:
    if not isinstance(field, dict):
        return False
    value = field.get("fieldValue")
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return False
    try:
        parsed = json.loads(text)
    except Exception:
        return False
    return runninghub_is_workflow_link_value(parsed)


def runninghub_collect_workflow_fields(workflow_json: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    if not isinstance(workflow_json, dict):
        return fields
    for node_id, node_content in workflow_json.items():
        if not isinstance(node_content, dict):
            continue
        inputs = node_content.get("inputs")
        if not isinstance(inputs, dict):
            continue
        for field_name, raw_value in inputs.items():
            if runninghub_is_workflow_link_value(raw_value):
                continue
            if isinstance(raw_value, (dict, list)):
                field_value = json.dumps(raw_value, ensure_ascii=False)
            elif raw_value is None:
                field_value = ""
            else:
                field_value = str(raw_value)
            field_type = runninghub_infer_workflow_field_type(field_name, field_value)
            fields.append(
                {
                    "id": f"{node_id}::{field_name}",
                    "nodeId": str(node_id),
                    "fieldName": str(field_name),
                    "fieldValue": field_value,
                    "fieldType": field_type,
                    "label": str(field_name),
                    "enabled": False,
                    "sourceFromUpstream": True,
                    "group": str(
                        (node_content.get("_meta") or {}).get("title")
                        or node_content.get("class_type")
                        or node_content.get("_class")
                        or node_content.get("type")
                        or ""
                    ),
                    "note": "",
                    "imageOrder": 0,
                    "required": field_type == "IMAGE",
                }
            )
    return fields


def runninghub_provider_workflow_config(workflow_id: str) -> dict[str, Any] | None:
    key = runninghub_workflow_store_key(workflow_id)
    if not key:
        return None
    providers = provider_store.load_api_providers()
    provider = next((item for item in providers if item.get("id") == "runninghub"), None)
    if not provider:
        return None
    for entry in provider.get("rh_workflows") or []:
        entry_key = runninghub_workflow_store_key(entry.get("workflowId") or entry.get("id"))
        if entry_key != key:
            continue
        cfg = {
            "workflowId": key,
            "title": entry.get("title") or key,
            "description": entry.get("note") or entry.get("description") or "",
            "fields": [
                field
                for field in (runninghub_normalize_field(item) for item in (entry.get("fields") or []))
                if not runninghub_is_saved_link_field(field)
            ],
            "workflowJson": entry.get("workflowJson") if isinstance(entry.get("workflowJson"), dict) else {},
            "optionalImageMode": entry.get("optionalImageMode") or "prune-workflow",
            "raw": entry.get("raw") if isinstance(entry.get("raw"), dict) else {},
            "updatedAt": entry.get("updatedAt") or 0,
            "source": "api_providers",
        }
        return cfg if runninghub_workflow_config_has_payload(cfg) else None
    return None


def runninghub_select_workflow_config(
    local_cfg: dict[str, Any] | None,
    provider_cfg: dict[str, Any] | None,
    workflow_id: str = "",
) -> dict[str, Any] | None:
    static_cfg = runninghub_static_workflow_config(workflow_id)
    if isinstance(local_cfg, dict) and isinstance(provider_cfg, dict):
        try:
            local_updated = int(local_cfg.get("updatedAt") or 0)
        except Exception:
            local_updated = 0
        try:
            provider_updated = int(provider_cfg.get("updatedAt") or 0)
        except Exception:
            provider_updated = 0
        return provider_cfg if provider_updated > local_updated else local_cfg
    if isinstance(local_cfg, dict):
        return local_cfg
    if isinstance(provider_cfg, dict):
        return provider_cfg
    if static_cfg:
        return static_cfg
    return None


def runninghub_workflow_entry_from_config(cfg: dict[str, Any] | None, fallback: dict[str, Any] | None = None) -> dict[str, Any] | None:
    fallback = fallback if isinstance(fallback, dict) else {}
    key = runninghub_workflow_store_key((cfg or {}).get("workflowId") or fallback.get("workflowId") or fallback.get("id"))
    if not key:
        return None
    return provider_store.normalize_runninghub_entry(
        {
            "id": key,
            "workflowId": key,
            "title": (cfg or {}).get("title") or fallback.get("title") or fallback.get("name") or f"工作流 {key[-6:]}",
            "note": (cfg or {}).get("description") or fallback.get("note") or fallback.get("description") or "",
            "thumbnail": fallback.get("thumbnail") or "",
            "enabled": fallback.get("enabled", True),
            "fields": (cfg or {}).get("fields") or fallback.get("fields") or [],
            "workflowJson": (cfg or {}).get("workflowJson")
            if isinstance((cfg or {}).get("workflowJson"), dict)
            else fallback.get("workflowJson") or {},
            "optionalImageMode": (cfg or {}).get("optionalImageMode") or fallback.get("optionalImageMode") or "prune-workflow",
            "raw": (cfg or {}).get("raw") if isinstance((cfg or {}).get("raw"), dict) else fallback.get("raw") or {},
            "updatedAt": (cfg or {}).get("updatedAt") or fallback.get("updatedAt") or 0,
        },
        "workflow",
    )


def sync_runninghub_workflow_to_provider(cfg: dict[str, Any]) -> None:
    if not isinstance(cfg, dict):
        return
    key = runninghub_workflow_store_key(cfg.get("workflowId"))
    if not key:
        return
    providers = provider_store.load_api_providers()
    provider = next((item for item in providers if item.get("id") == "runninghub"), None)
    if not provider:
        provider = {
            "id": "runninghub",
            "name": "RunningHub",
            "base_url": RUNNINGHUB_DEFAULT_BASE_URL,
            "protocol": "runninghub",
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
            "rh_workflows": [],
        }
        providers.append(provider)
    workflows = provider.setdefault("rh_workflows", [])
    entry = None
    for item in workflows:
        item_key = runninghub_workflow_store_key(item.get("workflowId") or item.get("id"))
        if item_key == key:
            entry = item
            break
    if entry is None:
        entry = {
            "id": key,
            "workflowId": key,
            "title": cfg.get("title") or f"工作流 {key[-6:]}",
            "note": cfg.get("description") or "",
            "thumbnail": "",
            "enabled": True,
        }
        workflows.append(entry)
    entry.update(
        {
            "id": key,
            "workflowId": key,
            "title": cfg.get("title") or entry.get("title") or f"工作流 {key[-6:]}",
            "note": cfg.get("description") or "",
            "fields": [
                field
                for field in (runninghub_normalize_field(item) for item in (cfg.get("fields") or []))
                if not runninghub_is_saved_link_field(field)
            ],
            "workflowJson": cfg.get("workflowJson") if isinstance(cfg.get("workflowJson"), dict) else {},
            "optionalImageMode": cfg.get("optionalImageMode") or "prune-workflow",
            "raw": cfg.get("raw") if isinstance(cfg.get("raw"), dict) else {},
            "updatedAt": cfg.get("updatedAt") or now_ms(),
        }
    )
    if "enabled" not in entry:
        entry["enabled"] = True
    if "thumbnail" not in entry:
        entry["thumbnail"] = ""
    provider_store.save_api_providers([provider_store.normalize_provider(item) for item in providers])


def remove_runninghub_workflow_from_provider(workflow_id: str) -> None:
    key = runninghub_workflow_store_key(workflow_id)
    if not key:
        return
    providers = provider_store.load_api_providers()
    changed = False
    for provider in providers:
        if provider.get("id") != "runninghub":
            continue
        workflows = provider.get("rh_workflows") or []
        removed = next(
            (
                item
                for item in workflows
                if runninghub_workflow_store_key(item.get("workflowId") or item.get("id")) == key
            ),
            None,
        )
        kept = [
            item
            for item in workflows
            if runninghub_workflow_store_key(item.get("workflowId") or item.get("id")) != key
        ]
        static_provider = provider_store.load_static_runninghub_provider()
        static_workflow = next(
            (
                item
                for item in (static_provider or {}).get("rh_workflows", [])
                if runninghub_workflow_store_key(item.get("workflowId") or item.get("id")) == key
            ),
            None,
        )
        if static_workflow:
            tombstone = provider_store.normalize_runninghub_entry(
                {**static_workflow, **(removed or {}), "enabled": False, "hidden": True}, "workflow"
            )
            if tombstone:
                kept.append(tombstone)
        if static_workflow or len(kept) != len(workflows):
            provider["rh_workflows"] = kept
            changed = True
    if changed:
        provider_store.save_api_providers([provider_store.normalize_provider(item) for item in providers])


async def _parse_workflow_prompt(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("code") not in (0, "0"):
        raise HTTPException(
            status_code=400,
            detail=(raw.get("msg") if isinstance(raw, dict) else "") or f"RunningHub 工作流参数拉取失败：{raw}",
        )
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    prompt = data.get("prompt")
    workflow_json: dict[str, Any] = {}
    if isinstance(prompt, str) and prompt.strip():
        try:
            workflow_json = json.loads(prompt)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"RunningHub 工作流 JSON 解析失败：{exc}") from exc
    elif isinstance(prompt, dict):
        workflow_json = prompt
    return workflow_json


async def runninghub_app_info(webapp_id: str) -> dict[str, Any]:
    webapp_id = str(webapp_id or "").strip()
    if not webapp_id:
        raise HTTPException(status_code=400, detail="webappId 必填")
    provider = runninghub_provider()
    api_key = runninghub_api_key(provider)
    url = runninghub_endpoint_url(
        provider,
        f"/api/webapp/apiCallDemo?apiKey={urllib.parse.quote(api_key)}&webappId={urllib.parse.quote(webapp_id)}",
    )
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SHORT) as client:
        try:
            response = await client.get(url, headers=runninghub_app_headers(False))
            raw = response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text[:500]) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"请求 RunningHub 应用信息失败：{exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=json.dumps(raw, ensure_ascii=False)[:500])
    if isinstance(raw, dict) and raw.get("code") not in (0, "0", None):
        raise HTTPException(status_code=400, detail=raw.get("msg") or f"RunningHub 查询失败 code={raw.get('code')}")
    data = raw.get("data") if isinstance(raw, dict) else {}
    return {"success": True, "data": data or {}}


async def runninghub_submit(payload: RunningHubSubmitRequest) -> dict[str, Any]:
    webapp_id = str(payload.webappId or "").strip()
    if not webapp_id:
        raise HTTPException(status_code=400, detail="webappId 必填")
    provider = runninghub_provider()
    api_key = runninghub_api_key(provider, use_wallet=payload.useWallet)
    body: dict[str, Any] = {
        "apiKey": api_key,
        "webappId": webapp_id,
        "nodeInfoList": sanitize_runninghub_node_info_list(payload.nodeInfoList or []),
    }
    instance_type = str(payload.instanceType or "").strip()
    if instance_type:
        body["instanceType"] = instance_type
    url = runninghub_endpoint_url(provider, "/task/openapi/ai-app/run")
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SUBMIT) as client:
        try:
            response = await client.post(url, headers=runninghub_app_headers(True, payload.useWallet), json=body)
            raw = response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"提交 RunningHub 任务失败：{exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=json.dumps(raw, ensure_ascii=False)[:800])
    if isinstance(raw, dict) and raw.get("code") in (0, "0"):
        task_id = raw.get("data", {}).get("taskId") if isinstance(raw.get("data"), dict) else ""
        if not task_id:
            raise HTTPException(status_code=502, detail=f"RunningHub 未返回 taskId：{raw}")
        return {"success": True, "data": {"taskId": task_id, "raw": raw}}
    raise HTTPException(
        status_code=400, detail=(raw.get("msg") if isinstance(raw, dict) else "") or f"RunningHub 提交失败：{raw}"
    )


async def runninghub_workflow_submit(payload: RunningHubWorkflowSubmitRequest) -> dict[str, Any]:
    workflow_id = str(payload.workflowId or "").strip()
    if not workflow_id:
        raise HTTPException(status_code=400, detail="workflowId 必填")
    provider = runninghub_provider()
    api_key = runninghub_api_key(provider, use_wallet=payload.useWallet)
    body: dict[str, Any] = {
        "apiKey": api_key,
        "workflowId": workflow_id,
        "addMetadata": True,
    }
    if payload.nodeInfoList:
        body["nodeInfoList"] = sanitize_runninghub_node_info_list(payload.nodeInfoList)
    workflow_payload = payload.workflow
    if workflow_payload:
        if isinstance(workflow_payload, (dict, list)):
            body["workflow"] = json.dumps(sanitize_seed_like_workflow_values(workflow_payload), ensure_ascii=False)
        else:
            body["workflow"] = str(workflow_payload)
    url = runninghub_endpoint_url(provider, "/task/openapi/create")
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SUBMIT) as client:
        try:
            response = await client.post(url, headers=runninghub_app_headers(True, payload.useWallet), json=body)
            raw = response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"提交 RunningHub 工作流失败：{exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=json.dumps(raw, ensure_ascii=False)[:800])
    if isinstance(raw, dict) and raw.get("code") in (0, "0"):
        task_id = raw.get("data", {}).get("taskId") if isinstance(raw.get("data"), dict) else ""
        if not task_id:
            raise HTTPException(status_code=502, detail=f"RunningHub 工作流未返回 taskId：{raw}")
        return {"success": True, "data": {"taskId": task_id, "raw": raw}}
    raise HTTPException(
        status_code=400,
        detail=(raw.get("msg") if isinstance(raw, dict) else "") or f"RunningHub 工作流提交失败：{raw}",
    )


async def runninghub_workflow_info(workflow_id: str) -> dict[str, Any]:
    workflow_id = str(workflow_id or "").strip()
    if not workflow_id:
        raise HTTPException(status_code=400, detail="workflowId 必填")
    provider = runninghub_provider()
    api_key = runninghub_api_key(provider)
    url = runninghub_endpoint_url(provider, "/api/openapi/getJsonApiFormat")
    body = {"apiKey": api_key, "workflowId": workflow_id}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_WORKFLOW) as client:
        try:
            response = await client.post(url, headers=runninghub_app_headers(True), json=body)
            raw = response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"拉取 RunningHub 工作流参数失败：{exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=json.dumps(raw, ensure_ascii=False)[:800])
    workflow_json = await _parse_workflow_prompt(raw)
    node_info_list = runninghub_workflow_node_info_list(workflow_json)
    return {"success": True, "data": {"workflowId": workflow_id, "nodeInfoList": node_info_list, "raw": raw}}


def list_runninghub_workflows() -> dict[str, Any]:
    with RUNNINGHUB_WORKFLOW_LOCK:
        store = load_runninghub_workflow_store()
    merged = {workflow_id: cfg for workflow_id, cfg in store.items() if isinstance(cfg, dict)}
    for provider in provider_store.load_api_providers():
        if provider.get("id") != "runninghub":
            continue
        for entry in provider.get("rh_workflows") or []:
            workflow_id = runninghub_workflow_store_key(entry.get("workflowId") or entry.get("id"))
            if not workflow_id:
                continue
            provider_cfg = runninghub_provider_workflow_config(workflow_id)
            if provider_cfg:
                merged[workflow_id] = runninghub_select_workflow_config(merged.get(workflow_id), provider_cfg, workflow_id)
    items = []
    for workflow_id, cfg in merged.items():
        if not isinstance(cfg, dict):
            continue
        items.append(
            {
                "workflowId": workflow_id,
                "title": cfg.get("title") or workflow_id,
                "fieldCount": len(cfg.get("fields") or []),
                "updatedAt": cfg.get("updatedAt"),
                "description": cfg.get("description") or "",
            }
        )
    items.sort(key=lambda item: item["title"])
    return {"workflows": items}


def get_runninghub_workflow(workflow_id: str) -> dict[str, Any]:
    key = runninghub_workflow_store_key(workflow_id)
    if not key:
        raise HTTPException(status_code=400, detail="workflowId 必填")
    with RUNNINGHUB_WORKFLOW_LOCK:
        store = load_runninghub_workflow_store()
    cfg = store.get(key)
    provider_cfg = runninghub_provider_workflow_config(key)
    cfg = runninghub_select_workflow_config(cfg, provider_cfg, key)
    if not isinstance(cfg, dict):
        raise HTTPException(status_code=404, detail="RunningHub 工作流未找到")
    return {"workflow": cfg}


async def fetch_runninghub_workflow(payload: RunningHubWorkflowConfig) -> dict[str, Any]:
    workflow_id = runninghub_workflow_store_key(payload.workflowId)
    if not workflow_id:
        raise HTTPException(status_code=400, detail="workflowId 必填")
    provider = runninghub_provider()
    api_key = runninghub_api_key(provider)
    url = runninghub_endpoint_url(provider, "/api/openapi/getJsonApiFormat")
    body = {"apiKey": api_key, "workflowId": workflow_id}
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_WORKFLOW) as client:
        try:
            response = await client.post(url, headers=runninghub_app_headers(True), json=body)
            raw = response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to fetch RunningHub workflow parameters: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=json.dumps(raw, ensure_ascii=False)[:800])
    if not isinstance(raw, dict) or raw.get("code") not in (0, "0"):
        raise HTTPException(
            status_code=400,
            detail=(raw.get("msg") if isinstance(raw, dict) else "") or f"RunningHub workflow fetch failed: {raw}",
        )
    workflow_json = await _parse_workflow_prompt(raw)
    fields = runninghub_collect_workflow_fields(workflow_json)
    return {
        "success": True,
        "data": {
            "workflowId": workflow_id,
            "title": payload.title or workflow_id,
            "description": payload.description or "",
            "fields": fields,
            "workflowJson": workflow_json,
            "raw": raw,
        },
    }


def save_runninghub_workflow(workflow_id: str, payload: RunningHubWorkflowConfig) -> dict[str, Any]:
    key = runninghub_workflow_store_key(workflow_id)
    if not key:
        raise HTTPException(status_code=400, detail="workflowId 必填")
    fields = [
        field
        for field in (runninghub_normalize_field(item) for item in (payload.fields or []))
        if not runninghub_is_saved_link_field(field)
    ]
    cfg = {
        "workflowId": key,
        "title": (payload.title or key).strip() or key,
        "description": payload.description or "",
        "fields": fields,
        "workflowJson": payload.workflowJson or {},
        "optionalImageMode": payload.optionalImageMode or "prune-workflow",
        "raw": payload.raw or {},
        "updatedAt": now_ms(),
    }
    with RUNNINGHUB_WORKFLOW_LOCK:
        store = load_runninghub_workflow_store()
        store[key] = cfg
        save_runninghub_workflow_store(store)
    sync_runninghub_workflow_to_provider(cfg)
    return {"success": True, "workflow": cfg}


def delete_runninghub_workflow(workflow_id: str) -> dict[str, Any]:
    key = runninghub_workflow_store_key(workflow_id)
    if not key:
        raise HTTPException(status_code=400, detail="workflowId 必填")
    with RUNNINGHUB_WORKFLOW_LOCK:
        store = load_runninghub_workflow_store()
        provider_cfg = runninghub_provider_workflow_config(key)
        if key not in store and not provider_cfg:
            raise HTTPException(status_code=404, detail="RunningHub 工作流未找到")
        store.pop(key, None)
        save_runninghub_workflow_store(store)
    remove_runninghub_workflow_from_provider(key)
    return {"success": True}


async def runninghub_query(task_id: str) -> dict[str, Any]:
    task_id = str(task_id or "").strip()
    if not task_id:
        raise HTTPException(status_code=400, detail="taskId 必填")
    provider = runninghub_provider()
    api_key = runninghub_api_key(provider)
    url = runninghub_endpoint_url(provider, "/task/openapi/outputs")
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_QUERY) as client:
        try:
            response = await client.post(url, headers=runninghub_app_headers(True), json={"apiKey": api_key, "taskId": task_id})
            raw = response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"查询 RunningHub 任务失败：{exc}") from exc
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=json.dumps(raw, ensure_ascii=False)[:800])
        code = raw.get("code") if isinstance(raw, dict) else None
        status = "PENDING"
        urls: list[str] = []
        image_items: list[dict[str, Any]] = []
        if code in (0, "0"):
            status = "SUCCESS"
            for remote in runninghub_extract_outputs(raw.get("data")):
                try:
                    local_url = await runninghub_store_remote_output(client, remote)
                except Exception:
                    local_url = remote
                urls.append(local_url)
                image_items.append(image_output_meta(local_url))
        elif code in (804, "804"):
            status = "RUNNING"
        elif code in (813, "813"):
            status = "QUEUED"
        elif code in (805, "805"):
            status = "FAILED"
        else:
            status = "UNKNOWN"
        return {
            "success": True,
            "data": {
                "status": status,
                "urls": urls,
                "image_items": image_items,
                "failReason": runninghub_fail_reason(raw),
                "code": code,
                "raw": raw,
            },
        }


async def runninghub_upload_asset(payload: RunningHubUploadAssetRequest) -> dict[str, Any]:
    source_url = str(payload.url or "").strip()
    if not source_url:
        raise HTTPException(status_code=400, detail="url 必填")
    provider = runninghub_provider()
    api_key = runninghub_api_key(provider, use_wallet=payload.useWallet)
    filename = "asset.bin"
    content_type = "application/octet-stream"
    content = b""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_UPLOAD, follow_redirects=True) as client:
        path = runninghub_local_asset_path(source_url)
        if path:
            filename = os.path.basename(path)
            content_type = content_type_for_path(path)
            content = open(path, "rb").read()
        elif source_url.startswith(("http://", "https://")):
            response = await client.get(source_url)
            if not response.is_success:
                raise HTTPException(status_code=400, detail=f"下载素材失败 HTTP {response.status_code}")
            content = response.content
            content_type = response.headers.get("content-type") or content_type
            filename = os.path.basename(urllib.parse.urlsplit(source_url).path) or filename
        else:
            raise HTTPException(status_code=400, detail=f"不支持的素材地址：{source_url}")
        if not content:
            raise HTTPException(status_code=400, detail="素材为空，无法上传到 RunningHub")
        upload_url = runninghub_endpoint_url(provider, "/task/openapi/upload")
        files = {"file": (filename, content, content_type)}
        data = {"apiKey": api_key, "fileType": "input"}
        try:
            response = await client.post(
                upload_url, headers=runninghub_app_headers(False, payload.useWallet), data=data, files=files
            )
            raw = response.json()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"上传素材到 RunningHub 失败：{exc}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=json.dumps(raw, ensure_ascii=False)[:800])
    if (
        isinstance(raw, dict)
        and raw.get("code") in (0, "0")
        and isinstance(raw.get("data"), dict)
        and raw["data"].get("fileName")
    ):
        return {
            "success": True,
            "data": {"fileName": raw["data"]["fileName"], "fileType": raw["data"].get("fileType") or content_type},
        }
    raise HTTPException(
        status_code=400, detail=(raw.get("msg") if isinstance(raw, dict) else "") or f"RunningHub 上传失败：{raw}"
    )
