"""ComfyUI backend instance configuration."""

from __future__ import annotations

import os

from infinite_canvas.core.config import get_settings


def comfyui_instances() -> list[str]:
    raw = os.getenv("COMFYUI_INSTANCES", "").strip()
    if not raw:
        raw = get_settings().comfyui_instances
    return [s.strip() for s in raw.split(",") if s.strip()]
