"""Canvas AI endpoints — legacy parity."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.canvas_ai import CanvasLLMRequest, CanvasVideoRequest, CloudGenRequest, MsGenerateRequest
from infinite_canvas.services import canvas_llm, canvas_video, modelscope_generate

router = APIRouter(tags=["canvas-ai"])


@router.post("/generate")
async def generate_cloud(req: CloudGenRequest):
    return await modelscope_generate.generate_cloud_zimage(req)


@router.post("/api/canvas-video")
async def api_canvas_video(payload: CanvasVideoRequest):
    return await canvas_video.canvas_video(payload)


@router.post("/api/canvas-llm")
async def api_canvas_llm(payload: CanvasLLMRequest):
    return await canvas_llm.canvas_llm(payload)


@router.post("/api/ms/generate")
async def api_ms_generate(req: MsGenerateRequest):
    return await modelscope_generate.ms_generate(req)
