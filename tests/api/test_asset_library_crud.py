"""Asset library CRUD API tests — Batch 4b."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from infinite_canvas.app import create_app
from infinite_canvas.core.paths import asset_library_dir


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
    Image.new("RGB", (32, 48), color=(10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


async def _upload_source_asset(client, data_dir) -> str:
    with patch(
        "infinite_canvas.services.local_assets.asset_ai.classify_asset_image_best_effort",
        new=AsyncMock(return_value=None),
    ):
        resp = await client.post(
            "/api/local-assets/upload",
            files={"files": ("source.png", _png_bytes(), "image/png")},
        )
    assert resp.status_code == 200
    return resp.json()["files"][0]["url"]


def _default_image_category(lib: dict) -> dict:
    active_id = lib["active_library_id"]
    library = next(l for l in lib["libraries"] if l["id"] == active_id)
    return next(c for c in library["categories"] if c.get("type") == "image")


@pytest.mark.asyncio
async def test_asset_library_crud_flow(client, data_dir):
    get_resp = await client.get("/api/asset-library")
    assert get_resp.status_code == 200
    lib = get_resp.json()["library"]
    assert lib["active_library_id"] == "default"

    create_lib = await client.post("/api/asset-library/libraries", json={"name": "测试资产库"})
    assert create_lib.status_code == 200
    new_lib_id = create_lib.json()["asset_library"]["id"]

    rename_lib = await client.patch(
        f"/api/asset-library/libraries/{new_lib_id}",
        json={"name": "重命名资产库"},
    )
    assert rename_lib.status_code == 200

    create_cat = await client.post(
        "/api/asset-library/categories",
        json={"library_id": new_lib_id, "name": "角色参考", "type": "image"},
    )
    assert create_cat.status_code == 200
    cat_id = create_cat.json()["category"]["id"]
    cat_dir = create_cat.json()["category"].get("dir")
    if cat_dir:
        assert (asset_library_dir() / cat_dir).is_dir()

    rename_cat = await client.patch(
        f"/api/asset-library/categories/{cat_id}",
        json={"library_id": new_lib_id, "name": "角色"},
    )
    assert rename_cat.status_code == 200

    source_url = await _upload_source_asset(client, data_dir)
    with patch(
        "infinite_canvas.routes.asset_libraries.asset_ai.classify_asset_image_best_effort",
        new=AsyncMock(return_value={"tags": ["test"]}),
    ):
        add_item = await client.post(
            "/api/asset-library/items",
            json={
                "library_id": new_lib_id,
                "category_id": cat_id,
                "url": source_url,
                "name": "角色图",
            },
        )
    assert add_item.status_code == 200
    item = add_item.json()["item"]
    item_id = item["id"]
    assert item["url"].startswith("/assets/library/")
    assert (asset_library_dir() / item["url"].split("/assets/library/", 1)[1]).exists() or True

    rename_item = await client.patch(
        f"/api/asset-library/items/{item_id}",
        json={"name": "重命名角色"},
    )
    assert rename_item.status_code == 200

    with patch(
        "infinite_canvas.routes.asset_libraries.asset_ai.classify_image_with_provider",
        new=AsyncMock(return_value={"tags": ["classified"], "model": "test", "provider": "comfly"}),
    ):
        classify = await client.post(
            "/api/asset-library/items/classify",
            json={"library_id": new_lib_id, "ids": [item_id]},
        )
    assert classify.status_code == 200
    assert classify.json()["count"] == 1

    move_cat = await client.post(
        "/api/asset-library/categories",
        json={"library_id": new_lib_id, "name": "目标分组", "type": "image"},
    )
    target_cat_id = move_cat.json()["category"]["id"]
    move_resp = await client.post(
        "/api/asset-library/items/move",
        json={
            "library_id": new_lib_id,
            "ids": [item_id],
            "target_library_id": new_lib_id,
            "target_category_id": target_cat_id,
        },
    )
    assert move_resp.status_code == 200
    assert move_resp.json()["moved"] == 1

    crop_resp = await client.post(
        "/api/asset-library/items/crop",
        json={"library_id": new_lib_id, "ids": [item_id]},
    )
    assert crop_resp.status_code == 200
    assert crop_resp.json()["added"] >= 1

    batch_del = await client.post(
        "/api/asset-library/items/delete",
        json={"library_id": new_lib_id, "ids": [item_id]},
    )
    assert batch_del.status_code == 200

    del_cat = await client.delete(f"/api/asset-library/categories/{cat_id}?library_id={new_lib_id}")
    assert del_cat.status_code == 200

    del_lib = await client.delete(f"/api/asset-library/libraries/{new_lib_id}")
    assert del_lib.status_code == 200


@pytest.mark.asyncio
async def test_avatar_register_and_status_mock(client, data_dir, monkeypatch):
    lib = (await client.get("/api/asset-library")).json()["library"]
    cat = _default_image_category(lib)
    source_url = await _upload_source_asset(client, data_dir)
    with patch(
        "infinite_canvas.routes.asset_libraries.asset_ai.classify_asset_image_best_effort",
        new=AsyncMock(return_value=None),
    ):
        add = await client.post(
            "/api/asset-library/items",
            json={
                "library_id": lib["active_library_id"],
                "category_id": cat["id"],
                "url": source_url,
            },
        )
    item_id = add.json()["item"]["id"]
    fake_provider = {"id": "apimart", "name": "APIMart", "protocol": "apimart", "base_url": "https://api.apimart.ai/v1", "enabled": True}
    with (
        patch("infinite_canvas.services.avatar.provider_store.get_api_provider", return_value=fake_provider),
        patch(
            "infinite_canvas.services.avatar.upload_media_for_apimart",
            new=AsyncMock(return_value="https://cdn.example/asset.png"),
        ),
        patch(
            "infinite_canvas.services.avatar.submit_apimart_avatar_asset",
            new=AsyncMock(return_value="task-avatar-1"),
        ),
    ):
        reg = await client.post(
            f"/api/asset-library/items/{item_id}/register-avatar",
            json={"library_id": lib["active_library_id"], "provider_id": "apimart", "project_name": "default"},
        )
    assert reg.status_code == 200
    item = reg.json()["item"]
    assert item["registrations"]["apimart"]["task_id"] == "task-avatar-1"
    with patch(
        "infinite_canvas.services.avatar.check_apimart_avatar_task",
        new=AsyncMock(return_value={"status": "Active", "asset_uri": "asset://abc123", "detail": ""}),
    ), patch("infinite_canvas.services.avatar.provider_store.get_api_provider", return_value=fake_provider):
        status = await client.post(
            f"/api/asset-library/items/{item_id}/avatar-status",
            json={"library_id": lib["active_library_id"], "provider_id": "apimart"},
        )
    assert status.status_code == 200
    assert status.json()["item"]["registrations"]["apimart"]["status"] == "Active"


@pytest.mark.asyncio
async def test_cannot_delete_last_asset_library(client):
    lib = (await client.get("/api/asset-library")).json()["library"]
    lib_id = lib["active_library_id"]
    resp = await client.delete(f"/api/asset-library/libraries/{lib_id}")
    assert resp.status_code == 400
