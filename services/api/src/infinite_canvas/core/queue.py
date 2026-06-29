"""In-memory generation queue (legacy parity — shared process state)."""

from __future__ import annotations

from threading import Lock
from typing import Any

QUEUE: list[dict[str, Any]] = []
QUEUE_LOCK = Lock()
