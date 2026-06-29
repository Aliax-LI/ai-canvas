"""AI reference upload schemas — legacy parity."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Base64UploadRequest(BaseModel):
    data: str = ""
    name: str = ""
    content_type: str = ""


class LocalImageImportRequest(BaseModel):
    path: str = ""
    paths: list[str] = Field(default_factory=list)
