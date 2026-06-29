"""Jimeng (即梦) API routes."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.schemas.jimeng import JimengHelpRequest, JimengQueryMediaRequest
from infinite_canvas.services import jimeng

router = APIRouter(tags=["jimeng"])


@router.get("/api/jimeng/status")
async def jimeng_status():
    return await jimeng.jimeng_status()


@router.get("/api/jimeng/credit")
async def jimeng_credit():
    return await jimeng.jimeng_credit()


@router.post("/api/jimeng/logout")
async def jimeng_logout():
    return await jimeng.jimeng_logout()


@router.post("/api/jimeng/login/start")
async def jimeng_login_start():
    return await jimeng.jimeng_login_start()


@router.get("/api/jimeng/login/status")
async def jimeng_login_status():
    return await jimeng.jimeng_login_status()


@router.post("/api/jimeng/help")
async def jimeng_help(payload: JimengHelpRequest):
    return await jimeng.jimeng_help(payload)


@router.post("/api/jimeng/query-media")
async def jimeng_query_media(payload: JimengQueryMediaRequest):
    return await jimeng.jimeng_query_media(payload)
