from fastapi import APIRouter

from infinite_canvas.routes.ai_upload import router as ai_upload_router
from infinite_canvas.routes.asset_libraries import router as asset_libraries_router
from infinite_canvas.routes.canvas_assets import router as canvas_assets_router
from infinite_canvas.routes.canvases import router as canvases_router
from infinite_canvas.routes.comfyui import router as comfyui_router
from infinite_canvas.routes.conversations import router as conversations_router
from infinite_canvas.routes.data_store import router as data_store_router
from infinite_canvas.routes.history import router as history_router
from infinite_canvas.routes.jimeng import router as jimeng_router
from infinite_canvas.routes.local_assets import router as local_assets_router
from infinite_canvas.routes.media import router as media_router
from infinite_canvas.routes.online_image import router as online_image_router
from infinite_canvas.routes.prompt_libraries import router as prompt_libraries_router
from infinite_canvas.routes.providers import router as providers_router
from infinite_canvas.routes.runninghub import router as runninghub_router
from infinite_canvas.routes.shared_folders import router as shared_folders_router
from infinite_canvas.routes.system import router as system_router

api_router = APIRouter()
api_router.include_router(system_router)
api_router.include_router(history_router)
api_router.include_router(media_router)
api_router.include_router(ai_upload_router)
api_router.include_router(online_image_router)
api_router.include_router(canvas_assets_router)
api_router.include_router(local_assets_router)
api_router.include_router(asset_libraries_router)
api_router.include_router(prompt_libraries_router)
api_router.include_router(shared_folders_router)
api_router.include_router(comfyui_router)
api_router.include_router(runninghub_router)
api_router.include_router(jimeng_router)
api_router.include_router(canvases_router)
api_router.include_router(conversations_router)
api_router.include_router(providers_router)
api_router.include_router(data_store_router)
