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


def test_phase0_openapi_paths_are_subset_of_legacy() -> None:
    """Phase 0 scaffold exposes a small subset of legacy routes (plus documented additions)."""
    legacy_paths = _load_paths(LEGACY_BASELINE)
    phase0_paths = set(create_app().openapi().get("paths", {}))

    assert phase0_paths, "Phase 0 app should expose at least one path"
    assert len(phase0_paths) < len(legacy_paths), (
        f"Phase 0 ({len(phase0_paths)} paths) should be smaller than legacy ({len(legacy_paths)})"
    )

    shared = phase0_paths - PHASE0_ONLY_PATHS
    extra = shared - legacy_paths
    assert not extra, f"Phase 0 paths not in legacy baseline: {sorted(extra)}"


def test_phase0_baseline_fixture_matches_app() -> None:
    """Committed Phase 0 fixture stays in sync with create_app()."""
    if not PHASE0_BASELINE.is_file():
        pytest.skip("openapi_baseline.json not generated yet")

    fixture_paths = _load_paths(PHASE0_BASELINE)
    app_paths = set(create_app().openapi().get("paths", {}))
    assert fixture_paths == app_paths
