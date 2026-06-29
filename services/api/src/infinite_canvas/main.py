"""CLI entry: uv run infinite-canvas"""

from __future__ import annotations

import argparse

import uvicorn

from infinite_canvas.app import create_app
from infinite_canvas.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Infinite Canvas migration API")
    parser.add_argument("--host", default=None, help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Bind port (default: 3000)")
    parser.add_argument("--data-dir", default=None, help="User data directory override")
    args = parser.parse_args()

    if args.data_dir:
        import os

        os.environ["INFINITE_CANVAS_DATA"] = args.data_dir
        get_settings.cache_clear()

    settings = get_settings()
    host = args.host or settings.host
    port = args.port or settings.port

    app = create_app()
    uvicorn.run(
        app,
        host=host,
        port=port,
        ws_ping_interval=None,
        ws_ping_timeout=None,
    )


if __name__ == "__main__":
    main()
