"""History and queue status endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter

from infinite_canvas.core.queue import QUEUE, QUEUE_LOCK
from infinite_canvas.services import history as history_service

router = APIRouter(tags=["history"])


class DeleteHistoryRequest(BaseModel):
    timestamp: float


@router.get("/api/history")
async def get_history_api(type: str | None = None):
    return history_service.get_history(type)


@router.get("/api/queue_status")
async def get_queue_status(client_id: str):
    with QUEUE_LOCK:
        total = len(QUEUE)
        positions = [i + 1 for i, task in enumerate(QUEUE) if task["client_id"] == client_id]
        position = positions[0] if positions else 0
    return {"total": total, "position": position}


@router.post("/api/history/delete")
async def delete_history(req: DeleteHistoryRequest):
    return history_service.delete_history(req.timestamp)
