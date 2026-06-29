"""ComfyUI backend instance configuration and load balancing."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from threading import Lock
from typing import Any

import requests

from infinite_canvas.core.config import get_settings
from infinite_canvas.core.env_file import update_env_values

LOAD_LOCK = Lock()
BACKEND_LOCAL_LOAD: dict[str, int] = {}

MEDIA_INPUT_KEYS = ("image", "video", "audio", "mask", "filename", "file")
MEDIA_INPUT_EXT_RE = re.compile(
    r"\.(png|jpe?g|webp|gif|bmp|tiff?|mp4|webm|mov|m4v|avi|mkv|mp3|wav|m4a|aac|ogg|flac)(?:\?|$)",
    re.I,
)


def comfyui_instances() -> list[str]:
    raw = os.getenv("COMFYUI_INSTANCES", "").strip()
    if not raw:
        raw = get_settings().comfyui_instances
    return [s.strip() for s in raw.split(",") if s.strip()]


def reload_comfyui_instances() -> list[str]:
    """Reload instances from environment after .env update."""
    global BACKEND_LOCAL_LOAD
    instances = comfyui_instances()
    new_load = {addr: 0 for addr in instances}
    for addr, count in (BACKEND_LOCAL_LOAD or {}).items():
        if addr in new_load:
            new_load[addr] = count
    BACKEND_LOCAL_LOAD = new_load
    return instances


def save_instances(instances: list[str]) -> list[str]:
    """Validate, persist, and reload ComfyUI instance addresses."""
    cleaned: list[str] = []
    for item in instances:
        s = str(item or "").strip()
        if not s:
            continue
        s = re.sub(r"^https?://", "", s)
        s = s.rstrip("/")
        if ":" not in s:
            raise ValueError(f"地址缺少端口号：{item}（应为 host:port，例如 127.0.0.1:8188）")
        host, _, port = s.rpartition(":")
        if not host or not port.isdigit():
            raise ValueError(f"地址不合法：{item}（应为 host:port，例如 127.0.0.1:8188）")
        if s in cleaned:
            continue
        cleaned.append(s)
    if not cleaned:
        raise ValueError("至少保留一个 ComfyUI 后端地址")
    update_env_values({"COMFYUI_INSTANCES": ",".join(cleaned)})
    os.environ["COMFYUI_INSTANCES"] = ",".join(cleaned)
    reload_comfyui_instances()
    try:
        import infinite_canvas.core.runtime_config as runtime_config

        runtime_config.COMFYUI_INSTANCES = cleaned
    except Exception:
        pass
    return cleaned


def check_images_exist(backend_addr: str, images: list[str] | None) -> bool:
    if not images:
        return True
    for img in images:
        try:
            url = f"http://{backend_addr}/view?filename={urllib.parse.quote(img)}&type=input"
            r = requests.get(url, stream=True, timeout=0.5)
            r.close()
            if r.status_code != 200:
                return False
        except Exception:
            return False
    return True


def is_comfy_input_media_value(input_name: str, value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    key = str(input_name or "").lower()
    if any(token in key for token in MEDIA_INPUT_KEYS):
        return True
    return bool(MEDIA_INPUT_EXT_RE.search(value))


def collect_required_comfy_media(params: dict[str, Any]) -> list[str]:
    required: list[str] = []
    for node_inputs in (params or {}).values():
        if not isinstance(node_inputs, dict):
            continue
        for input_name, value in node_inputs.items():
            if is_comfy_input_media_value(input_name, value):
                required.append(value)
    return list(dict.fromkeys(required))


def reserve_best_backend(required_images: list[str] | None = None) -> str:
    instances = comfyui_instances()
    backend_stats: dict[str, dict[str, Any]] = {}
    for addr in instances:
        try:
            with urllib.request.urlopen(f"http://{addr}/queue", timeout=1) as response:
                data = json.loads(response.read())
                remote_load = len(data.get("queue_running", [])) + len(data.get("queue_pending", []))
                has_images = check_images_exist(addr, required_images)
                backend_stats[addr] = {"remote_load": remote_load, "has_images": has_images}
        except Exception as exc:
            print(f"Backend {addr} unreachable: {exc}")
            continue
    with LOAD_LOCK:
        best_backend = instances[0]
        min_load = float("inf")
        if backend_stats:
            for addr, stats in backend_stats.items():
                load = max(stats["remote_load"], BACKEND_LOCAL_LOAD.get(addr, 0))
                if load < min_load or (
                    load == min_load
                    and stats.get("has_images")
                    and not backend_stats.get(best_backend, {}).get("has_images")
                ):
                    min_load = load
                    best_backend = addr
        BACKEND_LOCAL_LOAD[best_backend] = BACKEND_LOCAL_LOAD.get(best_backend, 0) + 1
        return best_backend


def release_backend_load(target_backend: str) -> None:
    with LOAD_LOCK:
        if BACKEND_LOCAL_LOAD.get(target_backend, 0) > 0:
            BACKEND_LOCAL_LOAD[target_backend] -= 1


# Initialize load counters for configured instances.
reload_comfyui_instances()
