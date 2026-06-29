"""Prompt library CRUD API tests — Batch 4b."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

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


@pytest.mark.asyncio
async def test_prompt_library_crud_flow(client):
    get_resp = await client.get("/api/prompt-libraries")
    assert get_resp.status_code == 200
    body = get_resp.json()["library"]
    assert body["active_library_id"] == "system"
    assert any(lib["id"] == "system" for lib in body["libraries"])

    create_resp = await client.post("/api/prompt-libraries", json={"name": "我的库"})
    assert create_resp.status_code == 200
    created = create_resp.json()
    lib_id = created["prompt_library"]["id"]
    assert created["library"]["active_library_id"] == lib_id

    rename_resp = await client.patch(f"/api/prompt-libraries/{lib_id}", json={"name": "重命名库"})
    assert rename_resp.status_code == 200
    assert rename_resp.json()["prompt_library"]["name"] == "重命名库"

    add_item = await client.post(
        "/api/prompt-libraries/items",
        json={
            "library_id": lib_id,
            "name": "测试提示词",
            "category": "custom",
            "positive": "a beautiful landscape",
            "negative": "blur",
            "scene": "outdoor",
        },
    )
    assert add_item.status_code == 200
    item_id = add_item.json()["item"]["id"]

    patch_item = await client.patch(
        f"/api/prompt-libraries/items/{item_id}",
        json={"library_id": lib_id, "name": "更新提示词", "positive": "updated prompt"},
    )
    assert patch_item.status_code == 200
    assert patch_item.json()["item"]["name"] == "更新提示词"

    add_cat = await client.post(
        "/api/prompt-libraries/categories",
        json={"library_id": lib_id, "name": "自定义分组"},
    )
    assert add_cat.status_code == 200
    cat_id = add_cat.json()["category"]["id"]

    rename_cat = await client.patch(
        f"/api/prompt-libraries/categories/{cat_id}",
        json={"name": "重命名分组"},
    )
    assert rename_cat.status_code == 200

    batch_del = await client.post(
        "/api/prompt-libraries/items/delete",
        json={"ids": [item_id]},
    )
    assert batch_del.status_code == 200
    assert batch_del.json()["removed"] == 1

    del_cat = await client.delete(f"/api/prompt-libraries/categories/{cat_id}")
    assert del_cat.status_code == 200

    del_lib = await client.delete(f"/api/prompt-libraries/{lib_id}")
    assert del_lib.status_code == 200
    assert del_lib.json()["library"]["active_library_id"] == "system"


@pytest.mark.asyncio
async def test_cannot_delete_system_prompt_library(client):
    resp = await client.delete("/api/prompt-libraries/system")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_add_prompt_item_requires_positive(client):
    get_resp = await client.get("/api/prompt-libraries")
    lib_id = get_resp.json()["library"]["active_library_id"]
    resp = await client.post("/api/prompt-libraries/items", json={"library_id": lib_id, "positive": ""})
    assert resp.status_code == 400
