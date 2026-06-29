import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

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


@pytest.mark.asyncio
async def test_canvas_llm_mock(client):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "画布 LLM 回复"}}]}

        def raise_for_status(self):
            return None

        @property
        def content(self):
            return b"x"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return FakeResponse()

    with patch("infinite_canvas.services.canvas_llm.httpx.AsyncClient", FakeClient):
        response = await client.post(
            "/api/canvas-llm",
            json={"message": "描述这张图", "provider": "lingjing"},
        )

    assert response.status_code == 200
    assert response.json()["text"] == "画布 LLM 回复"


@pytest.mark.asyncio
async def test_canvas_video_missing_api_key(client, monkeypatch):
    monkeypatch.delenv("API_PROVIDER_LINGJING_KEY", raising=False)
    response = await client.post(
        "/api/canvas-video",
        json={"prompt": "一只猫在跑", "provider_id": "lingjing"},
    )
    assert response.status_code == 400
    assert "API Key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_canvas_video_mock_upstream(client):
    class FakeResponse:
        status_code = 200
        text = json.dumps({"videos": ["https://cdn.example/video.mp4"]})

        def json(self):
            return {"videos": ["https://cdn.example/video.mp4"]}

        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return FakeResponse()

    with (
        patch("infinite_canvas.services.canvas_video.httpx.AsyncClient", FakeClient),
        patch(
            "infinite_canvas.services.canvas_video.save_remote_video_to_output",
            new_callable=AsyncMock,
            return_value="/assets/output/video_mock.mp4",
        ),
    ):
        response = await client.post(
            "/api/canvas-video",
            json={"prompt": "海浪视频", "provider_id": "lingjing", "model": "veo3-fast"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["videos"] == ["/assets/output/video_mock.mp4"]


@pytest.mark.asyncio
async def test_ms_generate_mock(client):
    class FakeResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._payload

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception("bad status")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self._poll = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            return FakeResponse(200, {"task_id": "task-ms-1"})

        async def get(self, url, **kwargs):
            return FakeResponse(200, {"task_status": "SUCCEED", "output_images": ["https://cdn.example/ms.png"]})

    with (
        patch("infinite_canvas.services.modelscope_generate.httpx.AsyncClient", FakeClient),
        patch("infinite_canvas.services.modelscope_generate.asyncio.sleep", new_callable=AsyncMock),
        patch(
            "infinite_canvas.services.modelscope_generate._download_modelscope_image",
            new_callable=AsyncMock,
            return_value="/assets/output/ms_mock.png",
        ),
        patch("infinite_canvas.services.modelscope_generate.resolve_modelscope_token", return_value="ms-token"),
    ):
        response = await client.post(
            "/api/ms/generate",
            json={"prompt": "一只狗", "model": "black-forest-labs/FLUX.2-klein-9B", "api_key": "ms-token"},
        )

    assert response.status_code == 200
    assert response.json()["url"] == "/assets/output/ms_mock.png"
