import io
from unittest.mock import AsyncMock, patch

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


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), color=(255, 128, 0)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_list_local_assets_empty(client):
    response = await client.get("/api/local-assets")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["tree"]["name"] == "全部上传"
    assert body["tree"]["count"] == 0


@pytest.mark.asyncio
async def test_upload_and_list_local_assets(client, data_dir):
    with patch(
        "infinite_canvas.services.local_assets.asset_ai.classify_asset_image_best_effort",
        new=AsyncMock(return_value=None),
    ):
        response = await client.post(
            "/api/local-assets/upload",
            files={"files": ("sample.png", _png_bytes(), "image/png")},
            data={"folder": "refs"},
        )
    assert response.status_code == 200
    files = response.json()["files"]
    assert len(files) == 1
    assert files[0]["kind"] == "image"
    assert files[0]["folder"] == "refs"
    assert files[0]["url"].startswith("/assets/uploads/")

    list_response = await client.get("/api/local-assets")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["natural_w"] == 16
    assert items[0]["natural_h"] == 16

    upload_dir = data_dir / "assets" / "uploads" / "refs"
    assert upload_dir.is_dir()
    assert any(p.suffix == ".png" for p in upload_dir.iterdir())


@pytest.mark.asyncio
async def test_local_asset_folder_crud(client):
    with patch(
        "infinite_canvas.services.local_assets.asset_ai.classify_asset_image_best_effort",
        new=AsyncMock(return_value=None),
    ):
        upload = await client.post(
            "/api/local-assets/upload",
            files={"files": ("a.png", _png_bytes(), "image/png")},
        )
    rel_path = upload.json()["files"][0]["file"]

    create = await client.post(
        "/api/local-assets/folders",
        json={"parent": "", "name": "batch-a"},
        headers=ORIGIN_HEADERS,
    )
    assert create.status_code == 200
    assert create.json()["folder"]["path"] == "batch-a"

    move = await client.post(
        "/api/local-assets/move",
        json={"names": [rel_path], "folder": "batch-a"},
        headers=ORIGIN_HEADERS,
    )
    assert move.status_code == 200
    assert move.json()["moved"] == 1

    save_caption = await client.patch(
        "/api/local-assets/caption",
        json={"name": f"batch-a/{rel_path.split('/')[-1]}", "caption": "测试提示词"},
    )
    assert save_caption.status_code == 200
    assert save_caption.json()["caption"] == "测试提示词"

    delete = await client.post(
        "/api/local-assets/delete",
        json={"names": [f"batch-a/{rel_path.split('/')[-1]}"]},
        headers=ORIGIN_HEADERS,
    )
    assert delete.status_code == 200
    assert len(delete.json()["deleted"]) == 1


@pytest.mark.asyncio
async def test_get_asset_library_defaults(client):
    response = await client.get("/api/asset-library")
    assert response.status_code == 200
    library = response.json()["library"]
    assert library["active_library_id"] == "default"
    assert len(library["libraries"]) >= 1
    cats = library["libraries"][0]["categories"]
    cat_ids = {c["id"] for c in cats}
    assert "characters" in cat_ids
    assert "scenes" in cat_ids


@pytest.mark.asyncio
async def test_get_prompt_libraries_defaults(client):
    response = await client.get("/api/prompt-libraries")
    assert response.status_code == 200
    library = response.json()["library"]
    assert library["active_library_id"] == "system"
    assert any(lib["id"] == "system" for lib in library["libraries"])
