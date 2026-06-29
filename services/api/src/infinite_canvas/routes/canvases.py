"""Canvas and project endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.canvas import (
    CanvasCreateRequest,
    CanvasMetaUpdate,
    CanvasSaveRequest,
    ProjectCreateRequest,
    ProjectUpdateRequest,
)
from infinite_canvas.services import canvas_store, projects

router = APIRouter(tags=["canvases"])


@router.get("/api/canvases")
async def canvases():
    return {"canvases": canvas_store.list_canvases()}


@router.get("/api/canvases/trash")
async def trashed_canvases():
    return {"canvases": canvas_store.list_deleted_canvases(), "retention_days": 30}


@router.post("/api/canvases")
async def create_canvas(payload: CanvasCreateRequest):
    return {
        "canvas": canvas_store.new_canvas(
            payload.title,
            payload.icon,
            payload.kind,
            payload.project,
            payload.board_x,
            payload.board_y,
        )
    }


@router.get("/api/canvases/{canvas_id}/meta")
async def get_canvas_meta(canvas_id: str):
    canvas = canvas_store.load_canvas(canvas_id)
    return {
        "id": canvas.get("id"),
        "updated_at": canvas.get("updated_at", 0),
        "title": canvas.get("title", "未命名画布"),
        "icon": canvas.get("icon", "layers"),
        "kind": canvas_store.normalize_canvas_kind(canvas.get("kind")),
    }


@router.post("/api/canvases/{canvas_id}/meta")
async def update_canvas_meta(canvas_id: str, payload: CanvasMetaUpdate):
    return {
        "canvas": canvas_store.update_canvas_meta(
            canvas_id, payload.model_dump(exclude_unset=True)
        )
    }


@router.get("/api/canvases/{canvas_id}")
async def get_canvas(canvas_id: str):
    return {"canvas": canvas_store.load_canvas(canvas_id)}


@router.post("/api/canvases/{canvas_id}/touch")
async def touch_canvas(canvas_id: str):
    canvas = canvas_store.load_canvas(canvas_id)
    canvas_store.save_canvas(canvas)
    return {
        "canvas": canvas_store.canvas_record(canvas),
        "updated_at": canvas.get("updated_at", 0),
    }


@router.put("/api/canvases/{canvas_id}")
async def update_canvas(canvas_id: str, payload: CanvasSaveRequest):
    return {
        "canvas": await canvas_store.update_canvas(
            canvas_id, payload.model_dump()
        )
    }


@router.delete("/api/canvases/{canvas_id}")
async def delete_canvas(canvas_id: str):
    return canvas_store.delete_canvas(canvas_id)


@router.post("/api/canvases/{canvas_id}/restore")
async def restore_canvas(canvas_id: str):
    return {"canvas": canvas_store.restore_canvas(canvas_id)}


@router.delete("/api/canvases/{canvas_id}/purge")
async def purge_canvas(canvas_id: str):
    return canvas_store.purge_canvas(canvas_id)


@router.get("/api/projects")
async def get_projects():
    return {"projects": projects.list_projects()}


@router.post("/api/projects")
async def create_project(payload: ProjectCreateRequest):
    return {"project": projects.project_record(projects.new_project(payload.name))}


@router.post("/api/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdateRequest):
    return {
        "project": projects.update_project(
            project_id, payload.name, payload.order
        )
    }


@router.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    return projects.delete_project(project_id)
