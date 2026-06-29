"""Pydantic models for asset library and prompt library endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AssetLibraryRequest(BaseModel):
    name: str = "资产库"


class AssetLibraryCategoryRequest(BaseModel):
    name: str = "新文件夹"
    type: str = "image"
    library_id: str = ""


class AssetLibraryAddRequest(BaseModel):
    category_id: str = ""
    url: str = ""
    name: str = ""
    library_id: str = ""


class AssetLibraryBatchAddRequest(BaseModel):
    category_id: str = ""
    library_id: str = ""
    items: list[AssetLibraryAddRequest] = Field(default_factory=list)


class AssetLibraryRenameRequest(BaseModel):
    name: str = ""
    library_id: str = ""


class AssetLibraryBatchDeleteRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)
    library_id: str = ""


class AssetLibraryBatchMoveRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)
    library_id: str = ""
    target_library_id: str = ""
    target_category_id: str = ""


class AssetLibraryBatchCropRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)
    library_id: str = ""
    target_library_id: str = ""
    target_category_id: str = ""
    mode: str = "square"


class AssetAvatarRegisterRequest(BaseModel):
    library_id: str = ""
    provider_id: str = ""
    project_name: str = "default"
    group_name: str = ""


class AssetLibraryClassifyRequest(BaseModel):
    library_id: str = ""
    ids: list[str] = Field(default_factory=list)
    provider: str = "comfly"
    model: str = ""
    ms_model: str = ""
    prompt: str = ""


class PromptLibraryRequest(BaseModel):
    name: str = "提示词库"


class PromptLibraryItemRequest(BaseModel):
    library_id: str = ""
    item_id: str = ""
    name: str = "提示词"
    category: str = "custom"
    positive: str = ""
    negative: str = ""
    scene: str = ""


class PromptLibraryBatchDeleteRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


class PromptLibraryCategoryRequest(BaseModel):
    name: str = "新分组"
    library_id: str = ""


class SharedFolderRegister(BaseModel):
    path: str = ""
    name: str = ""


class SharedFolderImport(BaseModel):
    library_id: str = ""
    category_id: str = ""
    folder_id: str = ""
    paths: list[str] = Field(default_factory=list)
