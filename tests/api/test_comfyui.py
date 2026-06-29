import base64
import io
import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from infinite_canvas.app import create_app

ORIGIN_HEADERS = {"Origin": "http://test"}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _png_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(0, 128, 255)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@pytest.mark.asyncio
async def test_get_comfyui_instances_default(client):
    response = await client.get("/api/comfyui/instances")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["instances"], list)
    assert len(body["instances"]) >= 1


@pytest.mark.asyncio
async def test_put_comfyui_instances(client, data_dir):
    response = await client.put(
        "/api/comfyui/instances",
        json={"instances": ["127.0.0.1:8188", "192.168.1.10:8189"]},
        headers=ORIGIN_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["instances"] == ["127.0.0.1:8188", "192.168.1.10:8189"]
    env_file = data_dir / "config" / ".env"
    assert env_file.is_file()
    assert "COMFYUI_INSTANCES" in env_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_list_workflows_empty(client):
    response = await client.get("/api/workflows")
    assert response.status_code == 200
    assert response.json() == {"workflows": []}


@pytest.mark.asyncio
async def test_upload_workflow_and_list(client, data_dir):
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "model.safetensors"}},
    }
    upload = await client.post(
        "/api/workflows",
        json={"name": "test-flow.json", "workflow": workflow},
        headers=ORIGIN_HEADERS,
    )
    assert upload.status_code == 200
    name = upload.json()["name"]
    assert name == "custom/test-flow.json"

    listed = await client.get("/api/workflows")
    assert listed.status_code == 200
    names = [item["name"] for item in listed.json()["workflows"]]
    assert name in names

    stored = data_dir / "workflows" / "custom" / "test-flow.json"
    assert stored.is_file()


@pytest.mark.asyncio
async def test_upload_comfyui_base64_mock(client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"name": "dx_mocked.png"}
    with patch("infinite_canvas.services.comfyui_generate.requests.post", return_value=mock_resp):
        response = await client.post(
            "/api/comfyui/upload-base64",
            json={"data": _png_b64(), "name": "ref.png", "content_type": "image/png"},
            headers=ORIGIN_HEADERS,
        )
    assert response.status_code == 200
    assert response.json()["name"] == "dx_mocked.png"


@pytest.mark.asyncio
async def test_image_params_default(client):
    response = await client.get("/api/image-params")
    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "api"
    assert body["submit"] == "/api/canvas-image-tasks"
    assert any(f.get("key") == "size" for f in body["fields"])
