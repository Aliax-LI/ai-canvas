import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from infinite_canvas.app import create_app
from infinite_canvas.schemas.comfyui import GenerateRequest


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    monkeypatch.setenv("COMFYUI_HISTORY_TIMEOUT", "2")
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _minimal_workflow() -> dict:
    return {
        "1": {"class_type": "SaveImage", "inputs": {"images": ["2", 0]}},
        "2": {"class_type": "EmptyImage", "inputs": {"width": 64, "height": 64}},
    }


def _history_payload(prompt_id: str) -> dict:
    return {
        prompt_id: {
            "outputs": {
                "1": {
                    "images": [
                        {
                            "filename": "out.png",
                            "subfolder": "",
                            "type": "output",
                        }
                    ]
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_generate_minimal_mock(client, data_dir):
    workflow_dir = data_dir / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_name = "custom/mock.json"
    (workflow_dir / "custom").mkdir(parents=True)
    (workflow_dir / "custom" / "mock.json").write_text(
        json.dumps(_minimal_workflow()), encoding="utf-8"
    )

    history = _history_payload("prompt-abc")

    class FakeResponse:
        def __init__(self, payload: bytes):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=10):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("/prompt"):
            return FakeResponse(json.dumps({"prompt_id": "prompt-abc"}).encode("utf-8"))
        if "/history/prompt-abc" in url:
            return FakeResponse(json.dumps(history).encode("utf-8"))
        if "/view?" in url:
            return FakeResponse(b"\x89PNG\r\n\x1a\n")
        raise RuntimeError(f"unexpected url: {url}")

    with (
        patch(
            "infinite_canvas.services.comfyui_generate.reserve_best_backend",
            return_value="127.0.0.1:8188",
        ),
        patch(
            "infinite_canvas.services.comfyui_generate.release_backend_load",
        ),
        patch("infinite_canvas.services.comfyui_generate.requests.get") as mock_get,
        patch("urllib.request.urlopen", side_effect=fake_urlopen),
    ):
        mock_get.return_value.status_code = 200
        mock_get.return_value.close.return_value = None
        response = await client.post(
            "/api/generate",
            json={
                "workflow_json": workflow_name,
                "type": "test",
                "client_id": "test-client",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert "error" not in body or not body.get("error")
    assert body.get("prompt_id") == "prompt-abc"
    assert body.get("backend") == "127.0.0.1:8188"
    assert isinstance(body.get("images"), list)


@pytest.mark.asyncio
async def test_generate_sync_unit(data_dir):
    from infinite_canvas.services import comfyui_generate

    workflow_dir = data_dir / "workflows" / "custom"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "unit.json").write_text(json.dumps(_minimal_workflow()), encoding="utf-8")

    history = _history_payload("pid-1")

    class FakeResponse:
        def __init__(self, payload: bytes):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=10):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if url.endswith("/prompt"):
            return FakeResponse(json.dumps({"prompt_id": "pid-1"}).encode("utf-8"))
        if "/history/pid-1" in url:
            return FakeResponse(json.dumps(history).encode("utf-8"))
        if "/view?" in url:
            return FakeResponse(b"\x89PNG\r\n\x1a\n")
        raise RuntimeError(f"unexpected url: {url}")

    with (
        patch("infinite_canvas.services.comfyui_generate.reserve_best_backend", return_value="127.0.0.1:8188"),
        patch("infinite_canvas.services.comfyui_generate.release_backend_load"),
        patch("infinite_canvas.services.comfyui_generate.requests.get") as mock_get,
        patch("urllib.request.urlopen", side_effect=fake_urlopen),
    ):
        mock_get.return_value.status_code = 200
        mock_get.return_value.close.return_value = None
        result = comfyui_generate.generate(
            GenerateRequest(workflow_json="custom/unit.json", type="unit-test", client_id="c1")
        )

    assert not result.get("error")
    assert result.get("images")
