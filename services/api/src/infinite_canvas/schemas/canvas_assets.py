"""Canvas assets and workflow export schemas — legacy parity."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CanvasAssetCheckRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)


class CanvasAssetDownloadRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    filename: str = "canvas-output-images.zip"


class CanvasWorkflowExportRequest(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    connections: list[dict[str, Any]] = Field(default_factory=list)
    filename: str = "canvas-workflow.zip"
    include_resources: bool = True
    library_id: str = ""
    category_id: str = ""
    name: str = ""
