#!/usr/bin/env python3
"""Export OpenAPI schema from running server or in-process app."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api" / "src"))
OUT = REPO_ROOT / "tests" / "fixtures" / "openapi_baseline.json"


def export_from_app() -> dict:
    from infinite_canvas.app import create_app

    app = create_app()
    return app.openapi()


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    schema = export_from_app()
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
