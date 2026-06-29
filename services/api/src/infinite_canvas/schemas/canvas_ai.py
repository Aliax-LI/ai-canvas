"""Canvas AI and ModelScope generation schemas — legacy parity."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field

from infinite_canvas.schemas.online_image import AIReference

VIDEO_PROMPT_MAX_LENGTH = int(os.getenv("VIDEO_PROMPT_MAX_LENGTH", "4000"))
LLM_MESSAGE_MAX_LENGTH = int(os.getenv("LLM_MESSAGE_MAX_LENGTH", "20000"))


class CanvasVideoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=VIDEO_PROMPT_MAX_LENGTH)
    provider_id: str = "comfly"
    model: str = "veo3-fast"
    duration: int = 5
    aspect_ratio: str = "16:9"
    resolution: str = ""
    size: str = ""
    images: list[AIReference] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)
    audios: list[str] = Field(default_factory=list)
    enhance_prompt: bool = False
    enable_upsample: bool = False
    watermark: bool = False
    seed: int | None = None
    camerafixed: bool = False
    return_last_frame: bool = False
    generate_audio: bool = False
    multimodal: bool = False
    trusted_asset: bool = False


class CanvasLLMRequest(BaseModel):
    message: str = Field(min_length=1, max_length=LLM_MESSAGE_MAX_LENGTH)
    system_prompt: str = ""
    model: str = ""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    provider: str = "comfly"
    ms_model: str = ""
    images: list[str] = Field(default_factory=list)
    videos: list[str] = Field(default_factory=list)


class CloudGenRequest(BaseModel):
    prompt: str
    api_key: str = ""
    model: str = ""
    resolution: str = "1024x1024"
    type: str = "zimage"
    image_urls: list[str] = Field(default_factory=list)
    loras: Any | None = None
    client_id: str | None = None


class CloudPollRequest(BaseModel):
    task_id: str
    api_key: str = ""
    client_id: str | None = None


class MsGenerateRequest(BaseModel):
    prompt: str
    api_key: str = ""
    model: str = "black-forest-labs/FLUX.2-klein-9B"
    image_urls: list[str] = Field(default_factory=list)
    width: int = 0
    height: int = 0
    size: str = ""
    loras: Any | None = None
    client_id: str | None = None
