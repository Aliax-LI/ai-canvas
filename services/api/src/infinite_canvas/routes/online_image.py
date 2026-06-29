"""Online image and canvas image task routes — Batch 7."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.online_image import ImageTaskQueryRequest, OnlineImageRequest
from infinite_canvas.services import online_image as online_image_service

router = APIRouter(tags=["online-image"])


@router.post("/api/online-image")
async def online_image(payload: OnlineImageRequest):
    return await online_image_service.build_online_image_result(payload)


@router.post("/api/image-task-query")
async def query_image_task(payload: ImageTaskQueryRequest):
    return await online_image_service.query_image_task(payload)


@router.post("/api/canvas-image-tasks")
async def create_canvas_image_task(payload: OnlineImageRequest):
    return online_image_service.create_canvas_image_task(payload)


@router.get("/api/canvas-image-tasks/{task_id}")
async def get_canvas_image_task(task_id: str):
    return online_image_service.get_canvas_image_task(task_id)
