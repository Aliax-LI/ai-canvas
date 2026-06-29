import json

import pytest
from httpx import ASGITransport, AsyncClient

from infinite_canvas.app import create_app
from infinite_canvas.core import queue as queue_module


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("INFINITE_CANVAS_DATA", str(tmp_path))
    return tmp_path


@pytest.fixture
async def client(data_dir):
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def clear_queue():
    with queue_module.QUEUE_LOCK:
        queue_module.QUEUE.clear()
    yield
    with queue_module.QUEUE_LOCK:
        queue_module.QUEUE.clear()


@pytest.mark.asyncio
async def test_get_history_empty(client):
    response = await client.get("/api/history")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_history_filters_and_sorts(client, data_dir):
    history_file = data_dir / "history.json"
    history_file.write_text(
        json.dumps(
            [
                {
                    "type": "zimage",
                    "timestamp": 100,
                    "images": ["/output/a.png"],
                },
                {
                    "type": "klein",
                    "timestamp": 300,
                    "images": ["/output/b.png"],
                },
                {
                    "type": "zimage",
                    "timestamp": 200,
                    "images": [],
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    response = await client.get("/api/history")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["timestamp"] == 300
    assert body[1]["timestamp"] == 100

    typed = await client.get("/api/history", params={"type": "klein"})
    assert typed.status_code == 200
    assert len(typed.json()) == 1
    assert typed.json()[0]["type"] == "klein"


@pytest.mark.asyncio
async def test_queue_status(client):
    missing = await client.get("/api/queue_status")
    assert missing.status_code == 422

    with queue_module.QUEUE_LOCK:
        queue_module.QUEUE.extend(
            [
                {"client_id": "a"},
                {"client_id": "b"},
                {"client_id": "a"},
            ]
        )

    response = await client.get("/api/queue_status", params={"client_id": "a"})
    assert response.status_code == 200
    assert response.json() == {"total": 3, "position": 1}

    absent = await client.get("/api/queue_status", params={"client_id": "missing"})
    assert absent.status_code == 200
    assert absent.json() == {"total": 3, "position": 0}


@pytest.mark.asyncio
async def test_delete_history_not_found(client):
    response = await client.post("/api/history/delete", json={"timestamp": 123.0})
    assert response.status_code == 200
    assert response.json() == {"success": False, "message": "History file not found"}


@pytest.mark.asyncio
async def test_delete_history_success(client, data_dir):
    history_file = data_dir / "history.json"
    history_file.write_text(
        json.dumps(
            [
                {"timestamp": 100.0, "images": []},
                {"timestamp": 200.0, "images": ["/output/missing.png"]},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    response = await client.post("/api/history/delete", json={"timestamp": 200.0})
    assert response.status_code == 200
    assert response.json() == {"success": True}

    remaining = json.loads(history_file.read_text(encoding="utf-8"))
    assert len(remaining) == 1
    assert remaining[0]["timestamp"] == 100.0


@pytest.mark.asyncio
async def test_delete_history_record_missing(client, data_dir):
    history_file = data_dir / "history.json"
    history_file.write_text(json.dumps([{"timestamp": 100.0, "images": []}]), encoding="utf-8")

    response = await client.post("/api/history/delete", json={"timestamp": 999.0})
    assert response.status_code == 200
    assert response.json() == {"success": False, "message": "Record not found"}
