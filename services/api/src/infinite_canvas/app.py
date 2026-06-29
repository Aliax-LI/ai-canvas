"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from infinite_canvas import __version__
from infinite_canvas.core.websocket import websocket_stats_handler
from infinite_canvas.core.paths import (
    ensure_app_data_dirs,
    legacy_assets_dir,
    legacy_output_dir,
    legacy_static_dir,
)
from infinite_canvas.routes import api_router


def create_app() -> FastAPI:
    ensure_app_data_dirs()

    app = FastAPI(
        title="Infinite Canvas",
        version=__version__,
        description="Migration API — Phase 0 scaffold",
    )

    app.include_router(api_router)

    @app.websocket("/ws/stats")
    async def websocket_stats(websocket: WebSocket, client_id: str | None = None):
        await websocket_stats_handler(websocket, client_id)

    static_dir = legacy_static_dir()
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        assets_dir = legacy_assets_dir()
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        output_dir = legacy_output_dir()
        if output_dir.is_dir():
            app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

        index_html = static_dir / "index.html"

        @app.get("/")
        def index():
            if index_html.is_file():
                return FileResponse(index_html)
            return JSONResponse({"detail": "index.html not found in legacy static"}, status_code=404)
    else:
        @app.get("/")
        def index_missing():
            return JSONResponse(
                {
                    "detail": "Legacy static not found. Clone upstream to coding/Infinite-Canvas/",
                    "expected": str(static_dir),
                },
                status_code=503,
            )

    return app
