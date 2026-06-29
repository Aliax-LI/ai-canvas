import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


@pytest.mark.asyncio
async def test_app_info(client):
    response = await client.get("/api/app-info")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "infinite-canvas"
    assert body["phase"] == "1-backend"
    assert body["storage"] in ("sqlite", "files")
    assert "database_path" in body
    assert "coding_root" in body
    assert "legacy_static_present" in body
