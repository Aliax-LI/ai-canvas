"""SQLite local storage for canvases, projects, conversations, and app settings."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from infinite_canvas.core.paths import database_file

SCHEMA_VERSION = 1
_INIT_LOCK = Lock()
_SCHEMA_PATH: Path | None = None

CANVAS_BODY_KEYS = ("nodes", "connections", "viewport", "logs", "settings")


def use_sqlite_storage() -> bool:
    """Default sqlite; set INFINITE_CANVAS_STORAGE=files to keep legacy JSON-only mode."""
    return os.getenv("INFINITE_CANVAS_STORAGE", "sqlite").strip().lower() != "files"


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS canvases (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            icon TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL DEFAULT 'classic',
            project_id TEXT NOT NULL DEFAULT 'default',
            owner TEXT NOT NULL DEFAULT '',
            color TEXT NOT NULL DEFAULT '',
            pinned INTEGER NOT NULL DEFAULT 0,
            board_x REAL,
            board_y REAL,
            deleted_at INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            body_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_canvases_project ON canvases(project_id);
        CREATE INDEX IF NOT EXISTS idx_canvases_deleted ON canvases(deleted_at);

        CREATE TABLE IF NOT EXISTS conversations (
            user_id TEXT NOT NULL,
            id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            body_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (user_id, id)
        );

        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);

        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    path = database_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        _apply_schema(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    global _SCHEMA_PATH
    path = database_file()
    if _SCHEMA_PATH == path:
        return
    with _INIT_LOCK:
        if _SCHEMA_PATH == path:
            return
        with db_connection():
            pass
        _SCHEMA_PATH = path


def is_migration_done() -> bool:
    init_database()
    with db_connection() as conn:
        row = conn.execute(
            "SELECT value FROM schema_meta WHERE key = 'files_migrated_v1'"
        ).fetchone()
        return bool(row and row["value"] == "1")


def mark_migration_done() -> None:
    with db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('files_migrated_v1', '1')"
        )


def store_stats() -> dict[str, Any]:
    init_database()
    with db_connection() as conn:
        def count(table: str) -> int:
            return int(conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"])

        canvas_active = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM canvases WHERE deleted_at IS NULL OR deleted_at = 0"
            ).fetchone()["c"]
        )
        canvas_trash = int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM canvases WHERE deleted_at IS NOT NULL AND deleted_at > 0"
            ).fetchone()["c"]
        )
        return {
            "projects": count("projects"),
            "canvases_active": canvas_active,
            "canvases_trash": canvas_trash,
            "conversations": count("conversations"),
            "settings_keys": count("app_settings"),
        }


def _canvas_body_from_doc(doc: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for key in CANVAS_BODY_KEYS:
        if key in doc:
            body[key] = doc[key]
    if "viewport" not in body:
        body["viewport"] = {"x": 0, "y": 0, "scale": 1}
    if "nodes" not in body:
        body["nodes"] = []
    if "connections" not in body:
        body["connections"] = []
    if "logs" not in body:
        body["logs"] = []
    if "settings" not in body:
        body["settings"] = {}
    return body


def _canvas_doc_from_row(row: sqlite3.Row) -> dict[str, Any]:
    body = json.loads(row["body_json"] or "{}")
    doc: dict[str, Any] = {
        "id": row["id"],
        "title": row["title"],
        "icon": row["icon"],
        "kind": row["kind"],
        "project": row["project_id"],
        "owner": row["owner"],
        "color": row["color"],
        "pinned": bool(row["pinned"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        **body,
    }
    if row["board_x"] is not None:
        doc["board_x"] = row["board_x"]
    if row["board_y"] is not None:
        doc["board_y"] = row["board_y"]
    deleted_at = row["deleted_at"]
    if deleted_at:
        doc["deleted_at"] = deleted_at
    return doc


def upsert_canvas(canvas: dict[str, Any]) -> None:
    init_database()
    body = _canvas_body_from_doc(canvas)
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO canvases (
                id, title, icon, kind, project_id, owner, color, pinned,
                board_x, board_y, deleted_at, created_at, updated_at, body_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                icon=excluded.icon,
                kind=excluded.kind,
                project_id=excluded.project_id,
                owner=excluded.owner,
                color=excluded.color,
                pinned=excluded.pinned,
                board_x=excluded.board_x,
                board_y=excluded.board_y,
                deleted_at=excluded.deleted_at,
                created_at=excluded.created_at,
                updated_at=excluded.updated_at,
                body_json=excluded.body_json
            """,
            (
                canvas["id"],
                canvas.get("title", "未命名画布"),
                canvas.get("icon", "🧩"),
                canvas.get("kind", "classic"),
                str(canvas.get("project") or "default"),
                str(canvas.get("owner") or ""),
                str(canvas.get("color") or ""),
                1 if canvas.get("pinned") else 0,
                canvas.get("board_x"),
                canvas.get("board_y"),
                int(canvas.get("deleted_at") or 0) or None,
                int(canvas.get("created_at") or 0),
                int(canvas.get("updated_at") or 0),
                json.dumps(body, ensure_ascii=False),
            ),
        )


def get_canvas(canvas_id: str) -> dict[str, Any] | None:
    init_database()
    with db_connection() as conn:
        row = conn.execute("SELECT * FROM canvases WHERE id = ?", (canvas_id,)).fetchone()
        return _canvas_doc_from_row(row) if row else None


def list_canvas_rows(*, include_deleted: bool) -> list[dict[str, Any]]:
    init_database()
    with db_connection() as conn:
        if include_deleted:
            rows = conn.execute(
                "SELECT * FROM canvases WHERE deleted_at IS NOT NULL AND deleted_at > 0"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM canvases WHERE deleted_at IS NULL OR deleted_at = 0"
            ).fetchall()
        return [_canvas_doc_from_row(row) for row in rows]


def delete_canvas_row(canvas_id: str) -> None:
    init_database()
    with db_connection() as conn:
        conn.execute("DELETE FROM canvases WHERE id = ?", (canvas_id,))


def purge_expired_trash(cutoff_ms: int) -> int:
    init_database()
    with db_connection() as conn:
        cur = conn.execute(
            "DELETE FROM canvases WHERE deleted_at IS NOT NULL AND deleted_at > 0 AND deleted_at < ?",
            (cutoff_ms,),
        )
        return cur.rowcount


def move_canvases_project(from_project: str, to_project: str) -> int:
    init_database()
    with db_connection() as conn:
        cur = conn.execute(
            "UPDATE canvases SET project_id = ? WHERE project_id = ?",
            (to_project, from_project),
        )
        return cur.rowcount


def replace_projects(projects: list[dict[str, Any]]) -> None:
    init_database()
    with db_connection() as conn:
        conn.execute("DELETE FROM projects")
        for project in projects:
            conn.execute(
                """
                INSERT INTO projects(id, name, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project["id"],
                    project.get("name", "未命名项目"),
                    int(project.get("order") or 0),
                    int(project.get("created_at") or 0),
                    int(project.get("updated_at") or 0),
                ),
            )


def load_projects_rows() -> list[dict[str, Any]]:
    init_database()
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY sort_order, created_at"
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "order": row["sort_order"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


def upsert_project(project: dict[str, Any]) -> None:
    init_database()
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO projects(id, name, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                sort_order=excluded.sort_order,
                updated_at=excluded.updated_at
            """,
            (
                project["id"],
                project.get("name", "未命名项目"),
                int(project.get("order") or 0),
                int(project.get("created_at") or 0),
                int(project.get("updated_at") or 0),
            ),
        )


def save_projects_batch(projects: list[dict[str, Any]]) -> None:
    replace_projects(projects)


def upsert_conversation(user_id: str, conversation: dict[str, Any]) -> None:
    init_database()
    body = {
        "messages": conversation.get("messages", []),
    }
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations(user_id, id, title, created_at, updated_at, body_json)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, id) DO UPDATE SET
                title=excluded.title,
                updated_at=excluded.updated_at,
                body_json=excluded.body_json
            """,
            (
                user_id,
                conversation["id"],
                conversation.get("title", "新对话"),
                int(conversation.get("created_at") or 0),
                int(conversation.get("updated_at") or 0),
                json.dumps(body, ensure_ascii=False),
            ),
        )


def get_conversation_row(user_id: str, conversation_id: str) -> dict[str, Any] | None:
    init_database()
    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? AND id = ?",
            (user_id, conversation_id),
        ).fetchone()
        if not row:
            return None
        body = json.loads(row["body_json"] or "{}")
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "messages": body.get("messages", []),
        }


def list_conversation_rows(user_id: str) -> list[dict[str, Any]]:
    init_database()
    with db_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            body = json.loads(row["body_json"] or "{}")
            messages = body.get("messages", [])
            last_message = next((m for m in reversed(messages) if m.get("role") != "system"), None)
            out.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "last_message": (last_message or {}).get("content", ""),
                }
            )
        return out


def delete_conversation_row(user_id: str, conversation_id: str) -> None:
    init_database()
    with db_connection() as conn:
        conn.execute(
            "DELETE FROM conversations WHERE user_id = ? AND id = ?",
            (user_id, conversation_id),
        )


def get_setting(key: str) -> Any | None:
    init_database()
    with db_connection() as conn:
        row = conn.execute("SELECT value_json FROM app_settings WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        return json.loads(row["value_json"])


def set_setting(key: str, value: Any, *, updated_at: int) -> None:
    init_database()
    with db_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings(key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json=excluded.value_json,
                updated_at=excluded.updated_at
            """,
            (key, json.dumps(value, ensure_ascii=False), updated_at),
        )


def list_setting_keys() -> list[str]:
    init_database()
    with db_connection() as conn:
        rows = conn.execute("SELECT key FROM app_settings ORDER BY key").fetchall()
        return [row["key"] for row in rows]
