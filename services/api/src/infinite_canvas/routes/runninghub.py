"""RunningHub API routes."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.runninghub import (
    RunningHubSubmitRequest,
    RunningHubUploadAssetRequest,
    RunningHubWorkflowConfig,
    RunningHubWorkflowSubmitRequest,
)
from infinite_canvas.services import runninghub

router = APIRouter(tags=["runninghub"])


@router.get("/api/runninghub/app-info")
async def runninghub_app_info(webappId: str = ""):
    return await runninghub.runninghub_app_info(webappId)


@router.post("/api/runninghub/submit")
async def runninghub_submit(payload: RunningHubSubmitRequest):
    return await runninghub.runninghub_submit(payload)


@router.post("/api/runninghub/workflow-submit")
async def runninghub_workflow_submit(payload: RunningHubWorkflowSubmitRequest):
    return await runninghub.runninghub_workflow_submit(payload)


@router.get("/api/runninghub/workflow-info")
async def runninghub_workflow_info(workflowId: str = ""):
    return await runninghub.runninghub_workflow_info(workflowId)


@router.get("/api/runninghub/workflows")
def list_runninghub_workflows():
    return runninghub.list_runninghub_workflows()


@router.get("/api/runninghub/workflows/{workflow_id:path}")
def get_runninghub_workflow(workflow_id: str):
    return runninghub.get_runninghub_workflow(workflow_id)


@router.post("/api/runninghub/workflows/fetch")
async def fetch_runninghub_workflow(payload: RunningHubWorkflowConfig):
    return await runninghub.fetch_runninghub_workflow(payload)


@router.put("/api/runninghub/workflows/{workflow_id:path}")
def save_runninghub_workflow(workflow_id: str, payload: RunningHubWorkflowConfig):
    return runninghub.save_runninghub_workflow(workflow_id, payload)


@router.delete("/api/runninghub/workflows/{workflow_id:path}")
def delete_runninghub_workflow(workflow_id: str):
    return runninghub.delete_runninghub_workflow(workflow_id)


@router.get("/api/runninghub/query")
async def runninghub_query(taskId: str = ""):
    return await runninghub.runninghub_query(taskId)


@router.post("/api/runninghub/upload-asset")
async def runninghub_upload_asset(payload: RunningHubUploadAssetRequest):
    return await runninghub.runninghub_upload_asset(payload)
