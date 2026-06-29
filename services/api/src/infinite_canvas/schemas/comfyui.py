"""ComfyUI and workflow request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ComfyInstancesPayload(BaseModel):
    instances: list[str] = []


class WorkflowField(BaseModel):
    id: str
    node: str = ""
    input: str = ""
    name: str = ""
    type: str = "text"
    default: Any = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    options: list[str] = []
    random_enabled: bool = False


class WorkflowConfig(BaseModel):
    title: str = ""
    fields: list[WorkflowField] = []
    mini_cards: dict[str, Any] = {}


class WorkflowUploadRequest(BaseModel):
    name: str
    workflow: dict[str, Any]


class WorkflowRunRequest(BaseModel):
    fields: dict[str, Any] = {}
    config: WorkflowConfig
    client_id: str = ""


class GenerateRequest(BaseModel):
    prompt: str = ""
    width: int = 1024
    height: int = 1024
    workflow_json: str = "Z-Image.json"
    params: dict[str, Any] = {}
    type: str = "zimage"
    client_id: str = ""
    convert_to_jpg: bool = False


class Base64UploadRequest(BaseModel):
    data: str = ""
    name: str = ""
    content_type: str = ""
