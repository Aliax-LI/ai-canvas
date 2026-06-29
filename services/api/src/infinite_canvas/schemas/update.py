"""App update request schemas — legacy parity."""

from __future__ import annotations

from pydantic import BaseModel


class UpdateRequest(BaseModel):
    auto_restart: bool = False
    restart_delay: int = 3
    source: str = "github"
    fallback: bool = True


class RollbackRequest(BaseModel):
    name: str = ""
    auto_restart: bool = False
    restart_delay: int = 3
