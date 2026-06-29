#!/usr/bin/env python3
"""Export OpenAPI schema from legacy coding/Infinite-Canvas/main.py FastAPI app."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = REPO_ROOT / "coding" / "Infinite-Canvas"
OUT = REPO_ROOT / "tests" / "fixtures" / "openapi_legacy_baseline.json"


def main() -> None:
    if not LEGACY_ROOT.is_dir():
        print(
            f"Error: legacy source not found at {LEGACY_ROOT}\n"
            "Clone upstream Infinite-Canvas to coding/Infinite-Canvas/ (gitignored).",
            file=sys.stderr,
        )
        sys.exit(1)

    sys.path.insert(0, str(LEGACY_ROOT))

    from main import app  # noqa: PLC0415 — legacy module on sys.path

    schema = app.openapi()
    path_count = len(schema.get("paths", {}))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({path_count} paths)")


if __name__ == "__main__":
    main()
