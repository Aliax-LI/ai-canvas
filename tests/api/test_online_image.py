import asyncio
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from infinite_canvas.app import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    monkeypatch.setenv("API_PROVIDER_LINGJING_KEY", "test-key")
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(10, 200, 50)).save(buf, format="PNG")
    return buf.getvalue()


def _mock_openai_image_response(image_url: str = "https://upstream.example/out.png") -> dict:
    return {"data": [{"url": image_url}]}


@pytest.mark.asyncio
async def test_online_image_openai_compat(client, data_dir):
    upstream_png = _png_bytes()

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict, text: str = ""):
            self.status_code = status_code
            self._payload = payload
            self.text = text or json.dumps(payload)

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"status {self.status_code}")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return FakeResponse(200, _mock_openai_image_response())

        async def get(self, url, **kwargs):
            req = MagicMock()
            req.raise_for_status = MagicMock()
            resp = MagicMock()
            resp.content = upstream_png
            resp.headers = {"Content-Type": "image/png"}
            resp.raise_for_status = MagicMock()
            return resp

    with patch("infinite_canvas.services.online_image.httpx.AsyncClient", FakeClient):
        response = await client.post(
            "/api/online-image",
            json={
                "prompt": "a red apple",
                "provider_id": "lingjing",
                "model": "gpt-image-2",
                "size": "1024x1024",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "online"
    assert len(body["images"]) == 1
    assert body["images"][0].startswith("/assets/output/")
    output_dir = data_dir / "assets" / "output"
    assert any(p.suffix == ".png" for p in output_dir.iterdir())


@pytest.mark.asyncio
async def test_online_image_modelscope_mock(client, monkeypatch):
    monkeypatch.setenv("API_PROVIDER_MODELSCOPE_KEY", "ms-key")
    fake_image = {"type": "url", "value": "https://cdn.example/ms.png"}

    with patch(
        "infinite_canvas.services.provider_image.generate_modelscope_provider_image",
        new=AsyncMock(return_value=(fake_image, {"task_status": "SUCCEED"})),
    ), patch(
        "infinite_canvas.services.online_image.save_ai_image_to_output",
        new=AsyncMock(return_value="/assets/output/ms_online.png"),
    ):
        response = await client.post(
            "/api/online-image",
            json={
                "prompt": "a blue sky",
                "provider_id": "modelscope",
                "model": "Tongyi-MAI/Z-Image-Turbo",
                "size": "1024x1024",
            },
        )
    assert response.status_code == 200
    assert response.json()["images"] == ["/assets/output/ms_online.png"]


@pytest.mark.asyncio
async def test_canvas_image_task_lifecycle(client):
    fake_result = {
        "prompt": "test",
        "images": ["/assets/output/online_abc.png"],
        "image_items": [{"url": "/assets/output/online_abc.png", "kind": "image"}],
        "timestamp": 1.0,
        "type": "online",
        "model": "gpt-image-2",
        "provider_id": "lingjing",
        "provider_name": "灵境API",
        "params": {},
    }

    with patch(
        "infinite_canvas.services.online_image.build_online_image_result",
        new=AsyncMock(return_value=fake_result),
    ):
        create = await client.post(
            "/api/canvas-image-tasks",
            json={"prompt": "async task", "provider_id": "lingjing", "model": "gpt-image-2"},
        )
        assert create.status_code == 200
        task_id = create.json()["task_id"]
        assert create.json()["status"] == "queued"

        for _ in range(40):
            poll = await client.get(f"/api/canvas-image-tasks/{task_id}")
            assert poll.status_code == 200
            task = poll.json()
            if task["status"] in {"succeeded", "failed"}:
                break
            await asyncio.sleep(0.05)
    assert task["status"] == "succeeded"
    assert task["result"]["images"]


@pytest.mark.asyncio
async def test_image_task_query_mock(client):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, url, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value={"data": {"status": "RUNNING"}})
            return resp

    with patch("infinite_canvas.services.online_image.httpx.AsyncClient", FakeClient):
        response = await client.post(
            "/api/image-task-query",
            json={"provider_id": "lingjing", "task_id": "task_test_123"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["task_id"] == "task_test_123"
