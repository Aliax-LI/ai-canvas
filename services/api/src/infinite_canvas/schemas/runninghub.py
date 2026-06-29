"""RunningHub API request schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunningHubSubmitRequest(BaseModel):
    webappId: str = ""
    nodeInfoList: list[dict[str, Any]] = []
    instanceType: str = ""
    useWallet: bool = False


class RunningHubWorkflowSubmitRequest(BaseModel):
    workflowId: str = ""
    nodeInfoList: list[dict[str, Any]] = []
    workflow: Any = None
    useWallet: bool = False


class RunningHubUploadAssetRequest(BaseModel):
    url: str = ""
    useWallet: bool = False


class RunningHubWorkflowConfigField(BaseModel):
    id: str = ""
    nodeId: str = ""
    fieldName: str = ""
    fieldValue: str = ""
    fieldType: str = "TEXT"
    label: str = ""
    enabled: bool = True
    sourceFromUpstream: bool = True
    group: str = ""
    note: str = ""
    options: list[str] = Field(default_factory=list)
    random_enabled: bool = False
    min: Any = ""
    max: Any = ""
    step: Any = ""
    imageOrder: int = 0
    required: bool = False


class RunningHubWorkflowConfig(BaseModel):
    workflowId: str = ""
    title: str = ""
    description: str = ""
    fields: list[RunningHubWorkflowConfigField] = Field(default_factory=list)
    workflowJson: dict[str, Any] = Field(default_factory=dict)
    optionalImageMode: str = "prune-workflow"
    raw: dict[str, Any] = Field(default_factory=dict)
