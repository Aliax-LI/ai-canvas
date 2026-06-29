"""FastAPI application factory."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from infinite_canvas import __version__
from infinite_canvas.core.env_file import ensure_runtime_config_files, load_env_file
from infinite_canvas.core.database import init_database, use_sqlite_storage
from infinite_canvas.core.websocket import set_global_loop, websocket_stats_handler
from infinite_canvas.core.paths import (
    app_assets_dir,
    ensure_app_data_dirs,
    legacy_assets_dir,
    legacy_output_dir,
    legacy_static_dir,
)
from infinite_canvas.routes import api_router
from infinite_canvas.services.data_migration import run_startup_migration


def create_app() -> FastAPI:
    ensure_app_data_dirs()
    ensure_runtime_config_files()
    load_env_file()
    if use_sqlite_storage():
        init_database()
        run_startup_migration()

    app = FastAPI(
        title="Infinite Canvas",
        version=__version__,
        description="Migration API — Phase 0 scaffold",
    )

    app.include_router(api_router)

    @app.on_event("startup")
    async def _on_startup() -> None:
        set_global_loop(asyncio.get_running_loop())

    @app.websocket("/ws/stats")
    async def websocket_stats(websocket: WebSocket, client_id: str | None = None):
        await websocket_stats_handler(websocket, client_id)

    static_dir = legacy_static_dir()
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        assets_dir = app_assets_dir()
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        else:
            legacy_assets = legacy_assets_dir()
            if legacy_assets.is_dir():
                app.mount("/assets", StaticFiles(directory=str(legacy_assets)), name="assets")

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
