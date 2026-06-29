"""ComfyUI instances, workflows, generate, and upload endpoints."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from infinite_canvas.core.comfyui import comfyui_instances, save_instances
from infinite_canvas.schemas.comfyui import (
    Base64UploadRequest,
    ComfyInstancesPayload,
    GenerateRequest,
    WorkflowConfig,
    WorkflowRunRequest,
    WorkflowUploadRequest,
)
from infinite_canvas.services import comfyui_generate, comfyui_workflows

router = APIRouter(tags=["comfyui"])


@router.get("/api/comfyui/instances")
def get_comfyui_instances():
    return {"instances": comfyui_instances()}


@router.put("/api/comfyui/instances")
def put_comfyui_instances(payload: ComfyInstancesPayload):
    try:
        cleaned = save_instances(payload.instances)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"写入 env 失败：{exc}") from exc
    return {"instances": cleaned}


@router.get("/api/workflows")
def list_workflows():
    return comfyui_workflows.list_workflows()


@router.get("/api/workflows/{name:path}")
def get_workflow(name: str):
    return comfyui_workflows.get_workflow(name)


@router.post("/api/workflows")
def upload_workflow(payload: WorkflowUploadRequest):
    return comfyui_workflows.upload_workflow(payload.name, payload.workflow)


@router.put("/api/workflows/{name:path}/config")
def save_workflow_config(name: str, payload: WorkflowConfig):
    return comfyui_workflows.save_workflow_config(name, payload.model_dump())


@router.delete("/api/workflows/{name:path}")
def delete_workflow(name: str):
    return comfyui_workflows.delete_workflow(name)


@router.post("/api/workflows/{name:path}/run")
def run_workflow(name: str, payload: WorkflowRunRequest):
    if not comfyui_workflows.WORKFLOW_NAME_RE.match(name):
        raise HTTPException(status_code=400, detail="Invalid workflow name")
    workflow_path = comfyui_workflows.workflow_path_from_name(name)
    if not workflow_path.is_file():
        raise HTTPException(status_code=404, detail="Workflow not found")
    params = comfyui_generate.workflow_run_params(payload.fields, payload.config.fields)
    req = GenerateRequest(
        prompt="",
        workflow_json=name,
        params=params,
        type="workflow-test",
        client_id=payload.client_id or str(uuid.uuid4()),
    )
    return comfyui_generate.generate(req)


@router.post("/api/generate")
def generate_api(req: GenerateRequest):
    return comfyui_generate.generate(req)


@router.post("/api/canvas-comfy-tasks")
async def create_canvas_comfy_task(payload: GenerateRequest):
    result = comfyui_generate.create_canvas_comfy_task(payload)
    asyncio.create_task(comfyui_generate.run_canvas_comfy_task(result["task_id"], payload))
    return result


@router.get("/api/canvas-comfy-tasks/{task_id}")
async def get_canvas_comfy_task(task_id: str):
    task = comfyui_generate.get_canvas_comfy_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="ComfyUI 任务不存在，可能服务已重启或任务已过期")
    return task


@router.post("/api/comfyui/upload-base64")
async def upload_comfyui_base64(payload: Base64UploadRequest):
    try:
        return comfyui_generate.upload_comfyui_base64(payload.data, payload.name, payload.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/image-params")
async def image_params(provider_id: str = "", model: str = ""):
    return comfyui_generate.image_params(provider_id, model)
