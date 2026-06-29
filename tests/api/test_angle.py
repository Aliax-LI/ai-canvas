import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from infinite_canvas.app import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    monkeypatch.setenv("MODELSCOPE_API_KEY", "ms-test-key")
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_angle_generate_mock(client):
    class FakeResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception("bad status")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return FakeResponse(200, {"task_id": "angle-task-1"})

        async def get(self, url, **kwargs):
            return FakeResponse(200, {"task_status": "SUCCEED", "output_images": ["https://cdn.example/angle.png"]})

    with (
        patch("infinite_canvas.services.modelscope_generate.httpx.AsyncClient", FakeClient),
        patch("infinite_canvas.services.modelscope_generate.asyncio.sleep", new_callable=AsyncMock),
        patch(
            "infinite_canvas.services.modelscope_generate._download_modelscope_image",
            new_callable=AsyncMock,
            return_value="/assets/output/angle_mock.png",
        ),
    ):
        response = await client.post(
            "/api/angle/generate",
            json={
                "prompt": "旋转 45 度",
                "api_key": "ms-key",
                "image_urls": ["/assets/input/ref.png"],
            },
        )

    assert response.status_code == 200
    assert response.json()["url"] == "/assets/output/angle_mock.png"


@pytest.mark.asyncio
async def test_angle_poll_status_mock(client):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"task_status": "SUCCEED", "output_images": ["https://cdn.example/resumed.png"]}

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            return FakeResponse()

    with (
        patch("infinite_canvas.services.modelscope_generate.httpx.AsyncClient", FakeClient),
        patch("infinite_canvas.services.modelscope_generate.asyncio.sleep", new_callable=AsyncMock),
        patch(
            "infinite_canvas.services.modelscope_generate._download_modelscope_image",
            new_callable=AsyncMock,
            return_value="/assets/output/angle_poll.png",
        ),
    ):
        response = await client.post(
            "/api/angle/poll_status",
            json={"task_id": "angle-task-2", "api_key": "ms-key"},
        )

    assert response.status_code == 200
    assert response.json()["url"] == "/assets/output/angle_poll.png"
