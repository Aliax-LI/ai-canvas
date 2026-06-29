"""Chat request schemas — legacy parity."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

from infinite_canvas.schemas.online_image import AIReference

LLM_MESSAGE_MAX_LENGTH = int(os.getenv("LLM_MESSAGE_MAX_LENGTH", "20000"))


class ChatRequest(BaseModel):
    conversation_id: str = ""
    message: str = Field(min_length=1, max_length=LLM_MESSAGE_MAX_LENGTH)
    system_prompt: str = ""
    model: str = ""
    image_model: str = ""
    image_provider: str = ""
    mode: str = "chat"
    size: str = "1024x1024"
    quality: str = "auto"
    reference_images: list[AIReference] = Field(default_factory=list)
    provider: str = "comfly"
    ms_model: str = ""
