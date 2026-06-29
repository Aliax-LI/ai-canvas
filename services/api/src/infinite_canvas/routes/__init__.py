from fastapi import APIRouter

from infinite_canvas.routes.canvases import router as canvases_router
from infinite_canvas.routes.history import router as history_router
from infinite_canvas.routes.media import router as media_router
from infinite_canvas.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(history_router)
api_router.include_router(media_router)
api_router.include_router(canvases_router)
