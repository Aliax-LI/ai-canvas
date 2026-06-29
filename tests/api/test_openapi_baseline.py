"""OpenAPI baseline fixtures — legacy full schema vs Phase 0 scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinite_canvas.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_BASELINE = REPO_ROOT / "tests" / "fixtures" / "openapi_legacy_baseline.json"
PHASE0_BASELINE = REPO_ROOT / "tests" / "fixtures" / "openapi_baseline.json"

# Routes not present in legacy main.py OpenAPI (migration / desktop additions).
PHASE0_ONLY_PATHS = frozenset({
    "/health",
    "/api/data/store",
    "/api/data/migrate-from-files",
})


def _load_paths(fixture: Path) -> set[str]:
    data = json.loads(fixture.read_text(encoding="utf-8"))
    return set(data.get("paths", {}))


def test_legacy_openapi_baseline_exists() -> None:
    assert LEGACY_BASELINE.is_file(), (
        f"Missing {LEGACY_BASELINE.name}; run: uv run python scripts/export_legacy_openapi.py"
    )


def test_legacy_openapi_has_expected_route_count() -> None:
    paths = _load_paths(LEGACY_BASELINE)
    assert len(paths) > 50, f"legacy baseline has only {len(paths)} paths; expected ~147"


def test_migrated_openapi_paths_cover_legacy() -> None:
    """Migrated app exposes all legacy routes plus documented additions."""
    legacy_paths = _load_paths(LEGACY_BASELINE)
    app_paths = set(create_app().openapi().get("paths", {}))

    assert app_paths, "App should expose at least one path"
    assert len(app_paths) >= len(legacy_paths) - 5, (
        f"App ({len(app_paths)} paths) should cover nearly all legacy ({len(legacy_paths)}) routes"
    )

    missing = legacy_paths - app_paths
    assert not missing, f"Legacy paths missing from app: {sorted(missing)}"

    shared = app_paths - PHASE0_ONLY_PATHS
    extra = shared - legacy_paths
    assert not extra, f"App paths not in legacy baseline: {sorted(extra)}"


def test_openapi_baseline_fixture_matches_app() -> None:
    """Committed OpenAPI fixture stays in sync with create_app()."""
    if not PHASE0_BASELINE.is_file():
        pytest.skip("openapi_baseline.json not generated yet")

    fixture_paths = _load_paths(PHASE0_BASELINE)
    app_paths = set(create_app().openapi().get("paths", {}))
    assert fixture_paths == app_paths
