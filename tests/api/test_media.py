import io
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

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


def _write_test_png(directory, name: str = "test.png") -> str:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    img = Image.new("RGB", (32, 32), color=(255, 0, 0))
    img.save(path, format="PNG")
    return f"/output/{name}"


@pytest.mark.asyncio
async def test_media_preview_not_found(client):
    response = await client.get("/api/media-preview", params={"url": "/output/missing.png"})
    assert response.status_code == 404
    assert response.json()["detail"] == "媒体文件不存在"


@pytest.mark.asyncio
async def test_media_preview_success(client, data_dir, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_CODING_ROOT", str(data_dir))
    output_dir = data_dir / "output"
    url = _write_test_png(output_dir)

    response = await client.get("/api/media-preview", params={"url": url, "w": 64})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


@pytest.mark.asyncio
async def test_image_jpeg_success(client, data_dir, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_CODING_ROOT", str(data_dir))
    output_dir = data_dir / "output"
    url = _write_test_png(output_dir)

    response = await client.get("/api/image-jpeg", params={"url": url, "w": 32})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_view_image_local_fallback(client, data_dir):
    input_dir = data_dir / "assets" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    path = input_dir / "ref.png"
    Image.new("RGB", (8, 8), color=(0, 255, 0)).save(path, format="PNG")

    with patch("infinite_canvas.services.media.comfyui_instances", return_value=[]):
        response = await client.get(
            "/api/view", params={"filename": "ref.png", "type": "input"}
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_view_image_not_found(client):
    with patch("infinite_canvas.services.media.comfyui_instances", return_value=[]):
        response = await client.get(
            "/api/view", params={"filename": "missing.png", "type": "input"}
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_output_local(client, data_dir, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_CODING_ROOT", str(data_dir))
    output_dir = data_dir / "output"
    url = _write_test_png(output_dir, "dl.png")

    response = await client.get("/api/download-output", params={"url": url})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_download_output_invalid_url(client):
    response = await client.get("/api/download-output", params={"url": "not-a-url"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_success(client):
    png = io.BytesIO()
    Image.new("RGB", (4, 4), color=(0, 0, 255)).save(png, format="PNG")
    png.seek(0)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"name": "uploaded.png"}

    with patch("infinite_canvas.services.media.requests.post", return_value=mock_response):
        with patch("infinite_canvas.services.media.comfyui_instances", return_value=["127.0.0.1:8188"]):
            response = await client.post(
                "/api/upload",
                files={"files": ("test.png", png.getvalue(), "image/png")},
            )
    assert response.status_code == 200
    assert response.json() == {"files": [{"comfy_name": "uploaded.png"}]}


@pytest.mark.asyncio
async def test_upload_failure(client):
    png = io.BytesIO()
    Image.new("RGB", (4, 4)).save(png, format="PNG")
    png.seek(0)

    with patch("infinite_canvas.services.media.requests.post", side_effect=Exception("down")):
        with patch("infinite_canvas.services.media.comfyui_instances", return_value=["127.0.0.1:8188"]):
            response = await client.post(
                "/api/upload",
                files={"files": ("test.png", png.getvalue(), "image/png")},
            )
    assert response.status_code == 500
