"""Shared folders API tests — Batch 4b."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

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


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_shared_folders_flow(client, data_dir):
    shared_dir = data_dir / "shared_media"
    shared_dir.mkdir()
    (shared_dir / "photo.png").write_bytes(_png_bytes())
    (shared_dir / "nested").mkdir()
    (shared_dir / "nested" / "inner.png").write_bytes(_png_bytes())

    empty = await client.get("/api/shared-folders")
    assert empty.status_code == 200
    assert empty.json()["folders"] == []

    reg = await client.post(
        "/api/shared-folders",
        json={"path": str(shared_dir), "name": "局域网素材"},
    )
    assert reg.status_code == 200
    folder = reg.json()["folder"]
    folder_id = folder["id"]
    assert folder["exists"] is True

    listed = await client.get("/api/shared-folders")
    assert listed.status_code == 200
    assert len(listed.json()["folders"]) == 1

    tree = await client.get(f"/api/shared-folders/{folder_id}/tree")
    assert tree.status_code == 200
    tree_body = tree.json()["tree"]
    assert tree_body["items"] or tree_body["children"]

    file_path = None
    if tree_body["items"]:
        file_path = tree_body["items"][0]["relativePath"]
    else:
        for child in tree_body["children"]:
            if child.get("items"):
                file_path = child["items"][0]["relativePath"]
                break
    assert file_path
    file_resp = await client.get(f"/api/shared-folders/{folder_id}/file?path={file_path}")
    assert file_resp.status_code == 200
    assert file_resp.headers["content-type"].startswith("image/")

    lib = (await client.get("/api/asset-library")).json()["library"]
    active_id = lib["active_library_id"]
    library = next(l for l in lib["libraries"] if l["id"] == active_id)
    cat = next(c for c in library["categories"] if c.get("type") == "image")
    with patch(
        "infinite_canvas.routes.shared_folders.asset_ai.classify_asset_image_best_effort",
        new=AsyncMock(return_value=None),
    ):
        imp = await client.post(
            "/api/shared-folders/import",
            json={
                "folder_id": folder_id,
                "library_id": active_id,
                "category_id": cat["id"],
                "paths": [file_path],
            },
        )
    assert imp.status_code == 200
    assert len(imp.json()["items"]) == 1

    unreg = await client.delete(f"/api/shared-folders/{folder_id}")
    assert unreg.status_code == 200
    assert unreg.json()["ok"] is True


@pytest.mark.asyncio
async def test_shared_folder_register_rejects_data_root(client, data_dir):
    resp = await client.post("/api/shared-folders", json={"path": str(data_dir)})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_shared_folder_file_not_found(client, data_dir):
    shared_dir = data_dir / "empty_shared"
    shared_dir.mkdir()
    reg = await client.post("/api/shared-folders", json={"path": str(shared_dir)})
    folder_id = reg.json()["folder"]["id"]
    resp = await client.get(f"/api/shared-folders/{folder_id}/file?path=missing.png")
    assert resp.status_code == 404
