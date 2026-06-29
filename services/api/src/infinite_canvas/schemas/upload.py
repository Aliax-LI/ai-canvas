"""Cloud upload request schemas — legacy parity."""

from __future__ import annotations

from pydantic import BaseModel


class TempShUploadRequest(BaseModel):
    url: str = ""


class CloudVideoUploadRequest(BaseModel):
    url: str = ""
    service: str = "auto"
