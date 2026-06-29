"""App update endpoints — legacy parity."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.update import RollbackRequest, UpdateRequest
from infinite_canvas.services import app_update

router = APIRouter(tags=["update"])


@router.get("/api/update-connectivity/probe")
def update_connectivity_probe(name: str):
    return app_update.update_connectivity_probe(name)


@router.get("/api/update-connectivity")
def update_connectivity():
    return app_update.update_connectivity()


@router.get("/api/check-update")
def check_update():
    return app_update.check_update()


@router.post("/api/update-from-github")
def update_from_github(req: UpdateRequest = UpdateRequest()):
    return app_update.update_from_github(req)


@router.get("/api/update-backups")
def get_update_backups():
    return {"backups": app_update.list_update_backups()}


@router.post("/api/update-rollback")
def rollback_update(req: RollbackRequest):
    return app_update.rollback_update(req)
