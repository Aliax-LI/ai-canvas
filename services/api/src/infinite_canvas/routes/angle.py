"""Angle generation endpoints — legacy parity."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.canvas_ai import CloudGenRequest, CloudPollRequest
from infinite_canvas.services import modelscope_generate

router = APIRouter(tags=["angle"])


@router.post("/api/angle/poll_status")
async def poll_angle_cloud(req: CloudPollRequest):
    return await modelscope_generate.poll_angle_status(req)


@router.post("/api/angle/generate")
async def generate_angle_cloud(req: CloudGenRequest):
    return await modelscope_generate.generate_angle(req)
