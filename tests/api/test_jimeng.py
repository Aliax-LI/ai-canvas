"""Jimeng API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

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
async def test_jimeng_status_cli_not_installed(client):
    with patch("infinite_canvas.services.jimeng.jimeng_cli_executable", return_value=""):
        response = await client.get("/api/jimeng/status")
    assert response.status_code == 200
    body = response.json()
    assert body["installed"] is False
    assert body["logged_in"] is False
    assert "dreamina CLI" in body["message"]


@pytest.mark.asyncio
async def test_jimeng_status_logged_in_mock(client):
    with (
        patch("infinite_canvas.services.jimeng.jimeng_cli_executable", return_value="/usr/bin/dreamina"),
        patch(
            "infinite_canvas.services.jimeng.jimeng_cli_version",
            new=AsyncMock(return_value=((1, 4, 2), "1.4.2")),
        ),
        patch(
            "infinite_canvas.services.jimeng.run_jimeng_cli",
            new=AsyncMock(return_value={"total_credit": 100}),
        ),
    ):
        response = await client.get("/api/jimeng/status")
    assert response.status_code == 200
    body = response.json()
    assert body["installed"] is True
    assert body["logged_in"] is True
    assert body["raw"]["total_credit"] == 100


@pytest.mark.asyncio
async def test_jimeng_query_media_requires_submit_id(client):
    response = await client.post("/api/jimeng/query-media", json={})
    assert response.status_code == 400
    assert "submit_id" in response.json()["detail"]
