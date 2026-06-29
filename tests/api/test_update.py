from unittest.mock import patch

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
async def test_check_update_mock(client):
    fake_github = {"version": "2026.07.01", "ok": True, "error": "", "url": "x", "source": "github"}
    fake_ms = {"version": "2026.06.01", "ok": True, "error": "", "url": "y", "source": "modelscope"}

    with patch("infinite_canvas.services.app_update.fetch_remote_version", side_effect=[fake_github, fake_ms]):
        response = await client.get("/api/check-update")

    assert response.status_code == 200
    body = response.json()
    assert body["github"]["ok"] is True
    assert "current" in body


@pytest.mark.asyncio
async def test_update_connectivity_mock(client):
    probe = {
        "name": "GitHub 版本文件",
        "url": "https://example/version",
        "ok": True,
        "status": 200,
        "elapsed_ms": 10,
        "error": "",
        "timed_out": False,
    }

    with patch("infinite_canvas.services.app_update.connectivity_probe", return_value=probe):
        response = await client.get("/api/update-connectivity")

    assert response.status_code == 200
    assert response.json()["results"]


@pytest.mark.asyncio
async def test_update_backups_empty(client):
    response = await client.get("/api/update-backups")
    assert response.status_code == 200
    assert response.json()["backups"] == []


@pytest.mark.asyncio
async def test_update_connectivity_probe_unknown(client):
    response = await client.get("/api/update-connectivity/probe", params={"name": "不存在"})
    assert response.status_code == 404
