"""Asset library and prompt library read endpoints — Batch 4 basics."""

from __future__ import annotations

from fastapi import APIRouter

from infinite_canvas.services import asset_library_store, prompt_library_store

router = APIRouter(tags=["asset-libraries"])


@router.get("/api/asset-library")
async def get_asset_library():
    return {"library": asset_library_store.load_asset_library()}


@router.get("/api/prompt-libraries")
async def get_prompt_libraries():
    return {"library": prompt_library_store.public_prompt_libraries()}
