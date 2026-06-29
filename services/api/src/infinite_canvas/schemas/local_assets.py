"""Pydantic models for local asset manager endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LocalAssetCaptionRequest(BaseModel):
    names: list[str] = []
    provider: str = "comfly"
    model: str = ""
    ms_model: str = ""
    prompt: str = "描述图片"


class LocalAssetCaptionSaveRequest(BaseModel):
    name: str = ""
    caption: str = ""


class LocalAssetClassifyRequest(BaseModel):
    names: list[str] = []
    provider: str = "comfly"
    model: str = ""
    ms_model: str = ""
    prompt: str = ""


class LocalAssetUrlImportItem(BaseModel):
    url: str = ""
    name: str = ""
    data: str = ""
    content_type: str = ""


class LocalAssetUrlImportRequest(BaseModel):
    items: list[LocalAssetUrlImportItem] = []
    folder: str = ""
    classify: bool = False
    provider: str = "comfly"
    model: str = ""
    ms_model: str = ""
    prompt: str = ""


class LocalAssetFolderRequest(BaseModel):
    parent: str = ""
    path: str = ""
    name: str = ""


class LocalAssetRenameRequest(BaseModel):
    path: str = ""
    name: str = ""


class LocalAssetDeleteRequest(BaseModel):
    names: list[str] = Field(default_factory=list)


class LocalAssetMoveRequest(BaseModel):
    names: list[str] = Field(default_factory=list)
    folder: str = ""
