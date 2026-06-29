import json

import pytest
from httpx import ASGITransport, AsyncClient

from infinite_canvas.app import create_app
from infinite_canvas.services import provider_store


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
async def test_get_config_returns_expected_keys(client):
    response = await client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "base_url",
        "chat_model",
        "image_model",
        "chat_models",
        "image_models",
        "video_models",
        "comfy_instances",
        "api_providers",
        "has_api_key",
        "ms_chat_models",
        "has_ms_key",
    ):
        assert key in body
    assert isinstance(body["api_providers"], list)
    assert len(body["api_providers"]) >= 4


@pytest.mark.asyncio
async def test_get_providers_list(client):
    response = await client.get("/api/providers")
    assert response.status_code == 200
    providers = response.json()["providers"]
    assert isinstance(providers, list)
    ids = {p["id"] for p in providers}
    assert "modelscope" in ids
    assert "runninghub" in ids


@pytest.mark.asyncio
async def test_put_providers_saves_and_returns(client, data_dir):
    defaults = provider_store.load_api_providers()
    payload = []
    for item in defaults:
        entry = {**item, "primary": item["id"] == "modelscope"}
        payload.append(entry)

    response = await client.put("/api/providers", json=payload)
    assert response.status_code == 200
    saved = response.json()["providers"]
    assert len(saved) == len(payload)
    assert all("has_key" in p for p in saved)

    from infinite_canvas.core.database import get_setting, use_sqlite_storage

    if use_sqlite_storage():
        stored = get_setting("api_providers")
        assert isinstance(stored, list)
        assert len(stored) == len(payload)
    else:
        providers_file = data_dir / "data" / "api_providers.json"
        assert providers_file.is_file()
        on_disk = json.loads(providers_file.read_text(encoding="utf-8"))
        assert len(on_disk) == len(payload)


@pytest.mark.asyncio
async def test_get_config_token_empty(client):
    response = await client.get("/api/config/token")
    assert response.status_code == 200
    assert response.json() == {"token": ""}


@pytest.mark.asyncio
async def test_get_models(client):
    response = await client.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert "chat_models" in body
    assert "image_models" in body
    assert "video_models" in body


@pytest.mark.asyncio
async def test_jimeng_test_connection_stub(client):
    response = await client.post(
        "/api/providers/test-connection",
        json={"provider_id": "jimeng", "protocol": "jimeng"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["image_models"]
