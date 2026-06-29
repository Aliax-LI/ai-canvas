"""Conversation CRUD — migrated from legacy main.py."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import HTTPException, Request

from infinite_canvas.core.database import (
    delete_conversation_row,
    get_conversation_row,
    list_conversation_rows,
    upsert_conversation,
    use_sqlite_storage,
)
from infinite_canvas.core.paths import conversations_dir

CONVERSATION_LOCK = Lock()


def now_ms() -> int:
    return int(time.time() * 1000)


def safe_user_id(user_id: str, request: Request) -> str:
    candidate = (user_id or "").strip()
    if not candidate and request.client:
        candidate = f"ip-{request.client.host}"
    if not candidate:
        candidate = "anonymous"
    candidate = re.sub(r"[^a-zA-Z0-9_.-]", "-", candidate)[:80].strip(".-")
    return candidate or "anonymous"


def user_dir(user_id: str) -> Path:
    path = conversations_dir() / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def conversation_path(user_id: str, conversation_id: str) -> Path:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", conversation_id or "")
    if not cleaned:
        raise HTTPException(status_code=400, detail="无效的对话 ID")
    return user_dir(user_id) / f"{cleaned}.json"


def save_conversation(user_id: str, conversation: dict[str, Any]) -> None:
    if use_sqlite_storage():
        with CONVERSATION_LOCK:
            upsert_conversation(user_id, conversation)
        return
    with CONVERSATION_LOCK:
        path = conversation_path(user_id, conversation["id"])
        path.write_text(json.dumps(conversation, ensure_ascii=False, indent=2), encoding="utf-8")


def new_conversation(user_id: str, title: str = "新对话") -> dict[str, Any]:
    timestamp = now_ms()
    conversation = {
        "id": uuid.uuid4().hex,
        "title": (title or "新对话")[:80],
        "created_at": timestamp,
        "updated_at": timestamp,
        "messages": [],
    }
    save_conversation(user_id, conversation)
    return conversation


def load_conversation(user_id: str, conversation_id: str) -> dict[str, Any]:
    if use_sqlite_storage():
        conversation = get_conversation_row(user_id, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="对话不存在")
        return conversation
    path = conversation_path(user_id, conversation_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="对话不存在")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def list_conversations(user_id: str) -> list[dict[str, Any]]:
    if use_sqlite_storage():
        return list_conversation_rows(user_id)
    records: list[dict[str, Any]] = []
    directory = user_dir(user_id)
    for file_path in directory.iterdir():
        if not file_path.name.endswith(".json"):
            continue
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        messages = data.get("messages", [])
        last_message = next((m for m in reversed(messages) if m.get("role") != "system"), None)
        records.append(
            {
                "id": data.get("id"),
                "title": data.get("title", "新对话"),
                "created_at": data.get("created_at", 0),
                "updated_at": data.get("updated_at", 0),
                "last_message": (last_message or {}).get("content", ""),
            }
        )
    return sorted(records, key=lambda item: item["updated_at"], reverse=True)


def delete_conversation(user_id: str, conversation_id: str) -> None:
    if use_sqlite_storage():
        delete_conversation_row(user_id, conversation_id)
        return
    path = conversation_path(user_id, conversation_id)
    if path.is_file():
        path.unlink()
