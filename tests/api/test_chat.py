import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from infinite_canvas.app import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    monkeypatch.setenv("API_PROVIDER_LINGJING_KEY", "test-chat-key")
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _chat_completion_response(content: str = "你好，我是助手。") -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}], "usage": {"total_tokens": 12}}


@pytest.mark.asyncio
async def test_chat_sync_mock_upstream(client):
    class FakeResponse:
        def __init__(self, payload: dict):
            self.status_code = 200
            self._payload = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._payload

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
            return FakeResponse(_chat_completion_response())

    with patch("infinite_canvas.services.chat.httpx.AsyncClient", FakeClient):
        response = await client.post(
            "/api/chat",
            json={"message": "你好", "provider": "lingjing", "model": "gpt-4o-mini"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["message"]["content"] == "你好，我是助手。"
    assert body["conversation"]["messages"][-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_chat_stream_mock_upstream(client):
    lines = [
        'data: {"choices":[{"delta":{"content":"你"}}]}',
        'data: {"choices":[{"delta":{"content":"好"}}]}',
        "data: [DONE]",
    ]

    class FakeStreamResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def aiter_lines(self):
            for line in lines:
                yield line

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def stream(self, *args, **kwargs):
            return FakeStreamResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    with patch("infinite_canvas.services.chat.httpx.AsyncClient", FakeClient):
        response = await client.post(
            "/api/chat/stream",
            json={"message": "流式测试", "provider": "lingjing"},
        )

    assert response.status_code == 200
    text = response.text
    assert "event-stream" in response.headers.get("content-type", "") or "delta" in text


@pytest.mark.asyncio
async def test_chat_agent_heuristic_generate_image(client):
    async def fake_generate(*args, **kwargs):
        return ({"type": "url", "value": "https://upstream.example/out.png"}, {"usage": {}})

    async def fake_save(*args, **kwargs):
        return "/assets/output/chat_mock.png"

    with (
        patch("infinite_canvas.services.chat.decide_chat_agent_action", new_callable=AsyncMock) as mock_decide,
        patch("infinite_canvas.services.chat.generate_ai_image", side_effect=fake_generate),
        patch("infinite_canvas.services.chat.save_ai_image_to_output", side_effect=fake_save),
    ):
        mock_decide.return_value = {"action": "generate_image", "prompt": "画一只猫", "reply": ""}
        response = await client.post(
            "/api/chat/agent",
            json={"message": "帮我画一只猫", "provider": "lingjing"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"]["action"] == "generate_image"
    assert body["message"]["type"] == "image"
