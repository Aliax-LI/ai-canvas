"""Canvas and project request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CanvasCreateRequest(BaseModel):
    title: str = "未命名画布"
    icon: str = "🧩"
    kind: str = "classic"
    project: str | None = None
    board_x: float | None = None
    board_y: float | None = None


class CanvasMetaUpdate(BaseModel):
    title: str | None = None
    icon: str | None = None
    owner: str | None = None
    color: str | None = None
    pinned: bool | None = None
    project: str | None = None
    board_x: float | None = None
    board_y: float | None = None


class ProjectCreateRequest(BaseModel):
    name: str = "新项目"


class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    order: int | None = None


class CanvasSaveRequest(BaseModel):
    title: str = "未命名画布"
    icon: str = "🧩"
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    connections: list[dict[str, Any]] = Field(default_factory=list)
    viewport: dict[str, Any] = Field(default_factory=dict)
    logs: list[dict[str, Any]] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)
    client_id: str = ""
    base_updated_at: int = 0
