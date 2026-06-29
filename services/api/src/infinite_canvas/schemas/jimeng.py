"""Jimeng (即梦) API request schemas."""

from __future__ import annotations

from pydantic import BaseModel


class JimengHelpRequest(BaseModel):
    command: str = ""


class JimengQueryMediaRequest(BaseModel):
    submit_id: str = ""
    kind: str = "image"
