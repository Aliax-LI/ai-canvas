import base64
import io
import json
import zipfile

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from infinite_canvas.app import create_app

ORIGIN_HEADERS = {"Origin": "http://test"}


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
    Image.new("RGB", (16, 16), color=(0, 128, 255)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_ai_reference(client, data_dir):
    response = await client.post(
        "/api/ai/upload",
        files={"files": ("ref.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 1
    assert files[0]["kind"] == "image"
    assert files[0]["url"].startswith("/assets/input/")
    saved = data_dir / "assets" / "input"
    assert any(p.suffix == ".png" for p in saved.iterdir())


@pytest.mark.asyncio
async def test_upload_ai_base64(client):
    b64 = base64.b64encode(_png_bytes()).decode("ascii")
    response = await client.post(
        "/api/ai/upload-base64",
        json={"data": b64, "name": "panel.png", "content_type": "image/png"},
    )
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 1
    assert files[0]["url"].startswith("/assets/input/")


@pytest.mark.asyncio
async def test_import_local_image(client, tmp_path):
    image_path = tmp_path / "local-ref.png"
    image_path.write_bytes(_png_bytes())
    response = await client.post(
        "/api/ai/import-local-image",
        json={"path": str(image_path)},
        headers=ORIGIN_HEADERS,
    )
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 1
    assert files[0]["kind"] == "image"
    assert files[0]["url"].startswith("/assets/input/")


@pytest.mark.asyncio
async def test_import_local_image_rejects_cross_origin(client, tmp_path):
    image_path = tmp_path / "local-ref.png"
    image_path.write_bytes(_png_bytes())
    response = await client.post(
        "/api/ai/import-local-image",
        json={"path": str(image_path)},
        headers={"Origin": "http://evil.example"},
    )
    assert response.status_code == 403
