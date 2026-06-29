import json

import pytest
from starlette.testclient import TestClient

from infinite_canvas.app import create_app
from infinite_canvas.core.websocket import manager


@pytest.fixture(autouse=True)
def reset_manager():
    manager.active_connections.clear()
    manager.user_connections.clear()
    manager.connection_clients.clear()
    yield
    manager.active_connections.clear()
    manager.user_connections.clear()
    manager.connection_clients.clear()


@pytest.fixture
def ws_client():
    with TestClient(create_app()) as client:
        yield client


def test_websocket_stats_on_connect(ws_client):
    with ws_client.websocket_connect("/ws/stats?client_id=ps_plugin_1") as ws:
        raw = ws.receive_text()
        payload = json.loads(raw)
        assert payload == {"type": "stats", "online_count": 1}


def test_websocket_ping_pong(ws_client):
    with ws_client.websocket_connect("/ws/stats?client_id=ps_plugin_1") as ws:
        ws.receive_text()
        ws.send_text("ping")
        raw = ws.receive_text()
        assert json.loads(raw) == {"type": "pong"}


def test_websocket_canvas_client_excluded_from_online_count(ws_client):
    with ws_client.websocket_connect("/ws/stats?client_id=canvas_abc") as ws:
        raw = ws.receive_text()
        assert json.loads(raw)["online_count"] == 0
