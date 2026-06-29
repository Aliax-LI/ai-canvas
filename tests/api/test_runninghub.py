"""RunningHub API tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
async def test_list_runninghub_workflows(client):
    response = await client.get("/api/runninghub/workflows")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["workflows"], list)
    if body["workflows"]:
        item = body["workflows"][0]
        assert "workflowId" in item
        assert "title" in item
        assert "fieldCount" in item


@pytest.mark.asyncio
async def test_runninghub_app_info_mock(client, monkeypatch):
    monkeypatch.setenv("RUNNINGHUB_API_KEY", "test-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"code": 0, "data": {"webappName": "demo"}}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("infinite_canvas.services.runninghub.httpx.AsyncClient", return_value=mock_client):
        response = await client.get("/api/runninghub/app-info", params={"webappId": "app-123"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["webappName"] == "demo"


@pytest.mark.asyncio
async def test_runninghub_app_info_requires_webapp_id(client):
    response = await client.get("/api/runninghub/app-info")
    assert response.status_code == 400
    assert "webappId" in response.json()["detail"]
