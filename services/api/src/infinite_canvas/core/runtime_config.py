"""Module-level runtime config synced from environment — legacy reload_env_globals parity."""

from __future__ import annotations

import os

from infinite_canvas.core.env_file import load_env_file
from infinite_canvas.core.provider_constants import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_IMAGE_MODEL,
    MODELSCOPE_DEFAULT_CHAT_MODELS,
)

load_env_file()

AI_BASE_URL = os.getenv("COMFLY_BASE_URL", "https://ai.comfly.chat").rstrip("/")
AI_API_KEY = os.getenv("COMFLY_API_KEY", "")
MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", DEFAULT_CHAT_MODEL)
IMAGE_MODEL = os.getenv("IMAGE_MODEL", DEFAULT_IMAGE_MODEL)
COMFYUI_INSTANCES = [
    s.strip() for s in os.getenv("COMFYUI_INSTANCES", "127.0.0.1:8188").split(",") if s.strip()
]

_VIDEO_DEFAULTS = [
    "veo2",
    "veo2-fast",
    "veo2-pro",
    "veo3",
    "veo3-fast",
    "veo3-pro",
    "veo3.1",
    "veo3.1-fast",
    "veo3.1-quality",
    "veo3.1-lite",
    "sora-2",
    "sora-2-pro",
    "wan2.6-t2v",
    "wan2.6-i2v",
    "wan2.5-t2v-preview",
    "wan2.5-i2v-preview",
    "wan2.2-t2v-plus",
    "wan2.2-i2v-plus",
    "wan2.2-i2v-flash",
    "doubao-seedance-2-0-260128",
    "doubao-seedance-2-0-fast-260128",
    "doubao-seedance-1-5-pro-251215",
    "doubao-seedance-1-0-pro-250528",
    "doubao-seedance-1-0-lite-t2v-250428",
    "doubao-seedance-1-0-lite-i2v-250428",
]


def model_list(env_name: str, primary: str, defaults: list[str]) -> list[str]:
    configured = os.getenv(env_name, "")
    configured_values = [item.strip() for item in configured.split(",") if item.strip()]
    values = configured_values or [primary, *defaults]
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


CHAT_MODELS = model_list(
    "CHAT_MODELS", os.getenv("CHAT_MODEL", CHAT_MODEL), ["gpt-4o-mini", "gemini-3.1-flash-image-preview-2k"]
)
IMAGE_MODELS = model_list("IMAGE_MODELS", os.getenv("IMAGE_MODEL", IMAGE_MODEL), ["nano-banana-pro"])
VIDEO_MODELS = model_list("VIDEO_MODELS", "veo3-fast", _VIDEO_DEFAULTS)
_configured_ms = [m.strip() for m in os.getenv("MODELSCOPE_CHAT_MODELS", "").split(",") if m.strip()]
MODELSCOPE_CHAT_MODELS = list(
    dict.fromkeys([m for m in [*MODELSCOPE_DEFAULT_CHAT_MODELS, *_configured_ms] if m])
)


def reload_env_globals() -> None:
    """Sync os.environ values back to module-level globals after provider save."""
    global MODELSCOPE_API_KEY, AI_API_KEY, AI_BASE_URL
    global IMAGE_MODELS, CHAT_MODELS, VIDEO_MODELS, MODELSCOPE_CHAT_MODELS, COMFYUI_INSTANCES

    MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY", "")
    AI_API_KEY = os.getenv("COMFLY_API_KEY", "")
    AI_BASE_URL = os.getenv("COMFLY_BASE_URL", "https://ai.comfly.chat").rstrip("/")
    IMAGE_MODELS = model_list("IMAGE_MODELS", os.getenv("IMAGE_MODEL", IMAGE_MODEL), ["nano-banana-pro"])
    CHAT_MODELS = model_list(
        "CHAT_MODELS",
        os.getenv("CHAT_MODEL", CHAT_MODEL),
        ["gpt-4o-mini", "gemini-3.1-flash-image-preview-2k"],
    )
    VIDEO_MODELS = model_list("VIDEO_MODELS", "veo3-fast", _VIDEO_DEFAULTS)
    _configured = [m.strip() for m in os.getenv("MODELSCOPE_CHAT_MODELS", "").split(",") if m.strip()]
    MODELSCOPE_CHAT_MODELS = list(
        dict.fromkeys([m for m in [*MODELSCOPE_DEFAULT_CHAT_MODELS, *_configured] if m])
    )
    COMFYUI_INSTANCES = [
        s.strip() for s in os.getenv("COMFYUI_INSTANCES", "127.0.0.1:8188").split(",") if s.strip()
    ]
    try:
        from infinite_canvas.core.comfyui import reload_comfyui_instances

        reload_comfyui_instances()
    except Exception:
        pass
