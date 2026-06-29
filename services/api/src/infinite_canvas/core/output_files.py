"""Resolve local filesystem paths from legacy /output and /assets URLs."""

from __future__ import annotations

import urllib.parse
from pathlib import Path

from infinite_canvas.core.paths import app_data_dir, legacy_assets_dir, legacy_output_dir


def output_file_from_url(url: str | dict | None) -> Path | None:
    if isinstance(url, dict):
        url = url.get("url", "")
    if not url or not (url.startswith("/output/") or url.startswith("/assets/")):
        return None

    clean = urllib.parse.unquote(url.split("?", 1)[0]).replace("\\", "/")
    if clean.startswith("/assets/"):
        rel = clean[len("/assets/") :].lstrip("/")
        roots = [app_data_dir() / "assets", legacy_assets_dir()]
    else:
        rel = clean[len("/output/") :].lstrip("/")
        roots = [legacy_output_dir()]

    if not rel:
        return None

    for root in roots:
        if not root.is_dir():
            continue
        root_resolved = root.resolve()
        path = (root / rel).resolve()
        try:
            path.relative_to(root_resolved)
        except ValueError:
            continue
        if path.is_file():
            return path
    return None
