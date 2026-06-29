"""Smart canvas schemas — legacy parity."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SmartCanvasGroupExportItem(BaseModel):
    kind: str = ""
    url: str = ""
    name: str = ""
    text: str = ""


class SmartCanvasGroupExportRequest(BaseModel):
    group_name: str = ""
    folder: str = ""
    items: list[SmartCanvasGroupExportItem] = Field(default_factory=list)
