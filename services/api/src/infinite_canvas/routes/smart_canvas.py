"""Smart canvas endpoints — legacy parity."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.smart_canvas import SmartCanvasGroupExportRequest
from infinite_canvas.services import smart_canvas

router = APIRouter(tags=["smart-canvas"])


@router.post("/api/smart-canvas/group-export")
async def export_smart_canvas_group(payload: SmartCanvasGroupExportRequest):
    return await smart_canvas.export_smart_canvas_group(payload)
