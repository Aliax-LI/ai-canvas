import json

import pytest
from httpx import ASGITransport, AsyncClient

from infinite_canvas.app import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_canvases_empty(client):
    response = await client.get("/api/canvases")
    assert response.status_code == 200
    assert response.json() == {"canvases": []}


@pytest.mark.asyncio
async def test_create_and_get_canvas(client):
    create = await client.post("/api/canvases", json={"title": "测试画布", "icon": "star"})
    assert create.status_code == 200
    canvas = create.json()["canvas"]
    assert canvas["title"] == "测试画布"
    assert canvas["icon"] == "star"
    canvas_id = canvas["id"]

    get_resp = await client.get(f"/api/canvases/{canvas_id}")
    assert get_resp.status_code == 200
    body = get_resp.json()["canvas"]
    assert body["title"] == "测试画布"
    assert body["nodes"] == []


@pytest.mark.asyncio
async def test_canvas_meta_and_touch(client):
    create = await client.post("/api/canvases", json={"title": "原名称"})
    canvas_id = create.json()["canvas"]["id"]

    meta = await client.get(f"/api/canvases/{canvas_id}/meta")
    assert meta.status_code == 200
    assert meta.json()["title"] == "原名称"

    update = await client.post(
        f"/api/canvases/{canvas_id}/meta",
        json={"title": "新名称", "pinned": True},
    )
    assert update.status_code == 200
    assert update.json()["canvas"]["title"] == "新名称"
    assert update.json()["canvas"]["pinned"] is True

    touch = await client.post(f"/api/canvases/{canvas_id}/touch")
    assert touch.status_code == 200
    assert touch.json()["canvas"]["title"] == "新名称"
    assert touch.json()["updated_at"] > 0


@pytest.mark.asyncio
async def test_update_canvas_put(client):
    create = await client.post("/api/canvases", json={"title": "保存测试"})
    canvas_id = create.json()["canvas"]["id"]
    base_updated_at = create.json()["canvas"]["updated_at"]

    put = await client.put(
        f"/api/canvases/{canvas_id}",
        json={
            "title": "已保存",
            "nodes": [{"id": "n1"}],
            "connections": [],
            "base_updated_at": base_updated_at,
        },
    )
    assert put.status_code == 200
    assert put.json()["canvas"]["title"] == "已保存"
    assert len(put.json()["canvas"]["nodes"]) == 1


@pytest.mark.asyncio
async def test_update_canvas_conflict(client):
    create = await client.post("/api/canvases", json={"title": "冲突测试"})
    canvas_id = create.json()["canvas"]["id"]

    conflict = await client.put(
        f"/api/canvases/{canvas_id}",
        json={"title": "旧版本", "base_updated_at": 1},
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_delete_restore_purge(client):
    create = await client.post("/api/canvases", json={"title": "回收站测试"})
    canvas_id = create.json()["canvas"]["id"]

    delete = await client.delete(f"/api/canvases/{canvas_id}")
    assert delete.status_code == 200
    assert delete.json() == {"ok": True}

    missing = await client.get(f"/api/canvases/{canvas_id}")
    assert missing.status_code == 404

    trash = await client.get("/api/canvases/trash")
    assert trash.status_code == 200
    assert trash.json()["retention_days"] == 30
    assert any(c["id"] == canvas_id for c in trash.json()["canvases"])

    restore = await client.post(f"/api/canvases/{canvas_id}/restore")
    assert restore.status_code == 200
    assert "deleted_at" not in restore.json()["canvas"]

    purge = await client.delete(f"/api/canvases/{canvas_id}/purge")
    assert purge.status_code == 200
    assert purge.json() == {"ok": True}

    gone = await client.get(f"/api/canvases/{canvas_id}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_projects_crud(client):
    listing = await client.get("/api/projects")
    assert listing.status_code == 200
    projects_list = listing.json()["projects"]
    assert any(p["id"] == "default" for p in projects_list)

    create = await client.post("/api/projects", json={"name": "我的项目"})
    assert create.status_code == 200
    project = create.json()["project"]
    assert project["name"] == "我的项目"
    project_id = project["id"]

    update = await client.post(
        f"/api/projects/{project_id}", json={"name": "重命名项目", "order": 5}
    )
    assert update.status_code == 200
    assert update.json()["project"]["name"] == "重命名项目"
    assert update.json()["project"]["order"] == 5

    canvas = await client.post(
        "/api/canvases", json={"title": "项目画布", "project": project_id}
    )
    assert canvas.status_code == 200

    delete_default = await client.delete("/api/projects/default")
    assert delete_default.status_code == 400

    delete = await client.delete(f"/api/projects/{project_id}")
    assert delete.status_code == 200
    assert delete.json()["ok"] is True
    assert delete.json()["moved"] == 1


@pytest.mark.asyncio
async def test_canvas_not_found(client):
    response = await client.get("/api/canvases/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_legacy_fallback_read(data_dir, monkeypatch):
    legacy_root = data_dir / "legacy"
    canvases = legacy_root / "data" / "canvases"
    canvases.mkdir(parents=True)
    canvas_id = "legacycanvas01"
    canvas_data = {
        "id": canvas_id,
        "title": "Legacy 画布",
        "icon": "layers",
        "kind": "classic",
        "nodes": [],
        "connections": [],
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "created_at": 1000,
        "updated_at": 2000,
    }
    (canvases / f"{canvas_id}.json").write_text(
        json.dumps(canvas_data, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setenv("INFINITE_CANVAS_CODING_ROOT", str(legacy_root))

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        migrate = await client.post("/api/data/migrate-from-files", json={"force": True})
        assert migrate.status_code == 200

        response = await client.get("/api/canvases")
        assert response.status_code == 200
        titles = [c["title"] for c in response.json()["canvases"]]
        assert "Legacy 画布" in titles
