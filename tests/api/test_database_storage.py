"""SQLite local storage tests."""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from infinite_canvas.app import create_app
from infinite_canvas.core.database import get_canvas, init_database, store_stats, use_sqlite_storage
from infinite_canvas.core.paths import database_file


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    monkeypatch.setenv("INFINITE_CANVAS_STORAGE", "sqlite")
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def test_sqlite_enabled_by_default(data_dir):
    assert use_sqlite_storage() is True
    init_database()
    assert database_file().is_file()


@pytest.mark.asyncio
async def test_canvas_persisted_in_sqlite(client):
    create = await client.post("/api/canvases", json={"title": "DB 画布"})
    assert create.status_code == 200
    canvas_id = create.json()["canvas"]["id"]

    canvas = get_canvas(canvas_id)
    assert canvas is not None
    assert canvas["title"] == "DB 画布"
    assert canvas["nodes"] == []


@pytest.mark.asyncio
async def test_projects_and_providers_in_sqlite(client):
    proj = await client.post("/api/projects", json={"name": "DB 项目"})
    assert proj.status_code == 200

    providers = await client.get("/api/providers")
    assert providers.status_code == 200
    assert isinstance(providers.json()["providers"], list)

    stats = store_stats()
    assert stats["projects"] >= 1


@pytest.mark.asyncio
async def test_conversations_in_sqlite(client):
    create = await client.post(
        "/api/conversations",
        json={"title": "DB 对话"},
        headers={"X-User-Id": "test-user"},
    )
    assert create.status_code == 200
    conv_id = create.json()["conversation"]["id"]

    listed = await client.get("/api/conversations", headers={"X-User-Id": "test-user"})
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()["conversations"]]
    assert conv_id in ids


@pytest.mark.asyncio
async def test_data_store_info(client):
    response = await client.get("/api/data/store")
    assert response.status_code == 200
    body = response.json()
    assert body["storage"] == "sqlite"
    assert body["database_exists"] is True
    assert "stats" in body


@pytest.mark.asyncio
async def test_migrate_from_json_files(data_dir, monkeypatch):
    canvases_dir = data_dir / "data" / "canvases"
    canvases_dir.mkdir(parents=True)
    legacy_canvas = {
        "id": "abc123",
        "title": "迁移画布",
        "icon": "layers",
        "kind": "classic",
        "project": "default",
        "created_at": 1,
        "updated_at": 2,
        "nodes": [{"id": "n1"}],
        "connections": [],
        "viewport": {"x": 0, "y": 0, "scale": 1},
    }
    (canvases_dir / "abc123.json").write_text(json.dumps(legacy_canvas), encoding="utf-8")

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        migrate = await ac.post("/api/data/migrate-from-files", json={"force": True})
        assert migrate.status_code == 200
        assert migrate.json()["imported"]["canvases"] >= 1

        listed = await ac.get("/api/canvases")
        titles = [item["title"] for item in listed.json()["canvases"]]
        assert "迁移画布" in titles
