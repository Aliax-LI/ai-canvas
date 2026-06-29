"""Runtime configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from infinite_canvas.core.paths import app_data_dir, coding_root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INFINITE_CANVAS_", extra="ignore")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=3000)
    data_dir: str = Field(default_factory=lambda: str(app_data_dir()))
    coding_root: str = Field(default_factory=lambda: str(coding_root()))
    comfyui_instances: str = Field(default="127.0.0.1:8188")


@lru_cache
def get_settings() -> Settings:
    return Settings()
