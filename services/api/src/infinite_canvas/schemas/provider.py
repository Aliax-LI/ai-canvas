"""Provider request schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from infinite_canvas.core.provider_constants import (
    VOLCENGINE_DEFAULT_PROJECT_NAME,
    VOLCENGINE_DEFAULT_REGION,
)


class ApiProviderPayload(BaseModel):
    id: str = ""
    name: str = ""
    base_url: str = ""
    protocol: str = "openai"
    image_request_mode: str = "openai"
    image_generation_endpoint: str = ""
    image_edit_endpoint: str = ""
    enabled: bool = True
    primary: bool = False
    image_models: list[str] = []
    chat_models: list[str] = []
    video_models: list[str] = []
    model_protocols: dict[str, str] = {}
    ms_loras: list[dict[str, Any]] = []
    ms_defaults_version: int = 0
    rh_apps: list[dict[str, Any]] = []
    rh_workflows: list[dict[str, Any]] = []
    volcengine_project_name: str = VOLCENGINE_DEFAULT_PROJECT_NAME
    volcengine_region: str = VOLCENGINE_DEFAULT_REGION
    volcengine_access_key_id: str | None = None
    volcengine_secret_access_key: str | None = None
    api_key: str | None = None
    wallet_api_key: str | None = None
    clear_key: bool = False
    clear_wallet_key: bool = False
    clear_volcengine_access_key_id: bool = False
    clear_volcengine_secret_access_key: bool = False


class TestConnectionPayload(BaseModel):
    base_url: str = ""
    api_key: str = ""
    provider_id: str = ""
    protocol: str = "openai"
    image_request_mode: str = "openai"
