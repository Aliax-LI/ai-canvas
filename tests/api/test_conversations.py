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
async def test_list_conversations_empty(client):
    response = await client.get("/api/conversations", headers={"X-User-Id": "test-user"})
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "test-user"
    assert body["conversations"] == []


@pytest.mark.asyncio
async def test_create_list_get_delete_conversation(client):
    create = await client.post(
        "/api/conversations",
        json={"title": "测试对话"},
        headers={"X-User-Id": "user-a"},
    )
    assert create.status_code == 200
    conversation = create.json()["conversation"]
    assert conversation["title"] == "测试对话"
    assert conversation["messages"] == []
    conversation_id = conversation["id"]

    listing = await client.get("/api/conversations", headers={"X-User-Id": "user-a"})
    assert listing.status_code == 200
    records = listing.json()["conversations"]
    assert len(records) == 1
    assert records[0]["id"] == conversation_id
    assert records[0]["title"] == "测试对话"

    get_resp = await client.get(
        f"/api/conversations/{conversation_id}",
        headers={"X-User-Id": "user-a"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["conversation"]["id"] == conversation_id

    delete = await client.delete(
        f"/api/conversations/{conversation_id}",
        headers={"X-User-Id": "user-a"},
    )
    assert delete.status_code == 200
    assert delete.json() == {"ok": True}

    missing = await client.get(
        f"/api/conversations/{conversation_id}",
        headers={"X-User-Id": "user-a"},
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_conversations_isolated_by_user(client):
    create = await client.post(
        "/api/conversations",
        json={"title": "私有对话"},
        headers={"X-User-Id": "owner"},
    )
    conversation_id = create.json()["conversation"]["id"]

    other = await client.get(
        f"/api/conversations/{conversation_id}",
        headers={"X-User-Id": "other-user"},
    )
    assert other.status_code == 404
