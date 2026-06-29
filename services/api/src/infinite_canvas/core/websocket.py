"""WebSocket connection manager — PS plugin / canvas client stats."""

from __future__ import annotations

import json
import time
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect


def now_ms() -> int:
    return int(time.time() * 1000)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, WebSocket] = {}
        self.connection_clients: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_clients[websocket] = client_id or f"anon-{id(websocket)}"
        if client_id:
            self.user_connections[client_id] = websocket
        print(
            f"WS Connected. Total: {len(self.active_connections)}, "
            f"Online: {self.online_count()}"
        )
        await self.broadcast_count()

    async def disconnect(self, websocket: WebSocket, client_id: str | None = None) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.connection_clients.pop(websocket, None)
        if client_id and self.user_connections.get(client_id) is websocket:
            del self.user_connections[client_id]
        print(
            f"WS Disconnected. Total: {len(self.active_connections)}, "
            f"Online: {self.online_count()}"
        )
        await self.broadcast_count()

    def online_count(self) -> int:
        visible_clients = {
            client_id
            for client_id in self.connection_clients.values()
            if client_id and not str(client_id).startswith("canvas_")
        }
        return len(visible_clients)

    async def broadcast_count(self) -> None:
        count = self.online_count()
        data = json.dumps({"type": "stats", "online_count": count})
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(data)
            except Exception as e:
                print(f"Broadcast error: {e}")
                self.active_connections.remove(connection)

    async def broadcast_new_image(self, image_data: dict) -> None:
        data = json.dumps({"type": "new_image", "data": image_data})
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(data)
            except Exception as e:
                print(f"Broadcast image error: {e}")
                self.active_connections.remove(connection)

    async def broadcast_canvas_updated(
        self, canvas_id: str, updated_at: int, client_id: str = ""
    ) -> None:
        data = json.dumps(
            {
                "type": "canvas_updated",
                "canvas_id": canvas_id,
                "updated_at": updated_at,
                "client_id": client_id or "",
            }
        )
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(data)
            except Exception as e:
                print(f"Broadcast canvas error: {e}")
                self.active_connections.remove(connection)

    async def broadcast_asset_library_updated(self, updated_at: int = 0) -> None:
        data = json.dumps(
            {
                "type": "asset_library_updated",
                "updated_at": updated_at or now_ms(),
            }
        )
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(data)
            except Exception as e:
                print(f"Broadcast asset library error: {e}")
                self.active_connections.remove(connection)

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        ws = self.user_connections.get(client_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                print(f"Personal message error for {client_id}: {e}")


manager = ConnectionManager()
GLOBAL_LOOP = None


def set_global_loop(loop) -> None:
    global GLOBAL_LOOP
    GLOBAL_LOOP = loop


async def websocket_stats_handler(
    websocket: WebSocket, client_id: str | None = None
) -> None:
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await manager.disconnect(websocket, client_id)
    except Exception as e:
        print(f"WS Error: {e}")
        await manager.disconnect(websocket, client_id)
