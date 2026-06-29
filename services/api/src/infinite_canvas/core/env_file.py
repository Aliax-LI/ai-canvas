"""Load and update API .env file under app data config/."""

from __future__ import annotations

import os
import re

from infinite_canvas.core.paths import api_env_file


def env_quote(value: str) -> str:
    text = str(value or "")
    if not text or re.search(r"\s|#|['\"]", text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def ensure_runtime_config_files() -> None:
    path = api_env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.parent.joinpath("data").mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.touch()


def load_env_file() -> None:
    path = api_env_file()
    if not path.is_file():
        return
    try:
        content = path.read_text(encoding="utf-8-sig")
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    except Exception as exc:
        print(f"加载 API/.env 失败: {exc}")


def read_api_env_value(key: str) -> str:
    key = str(key or "").strip()
    path = api_env_file()
    if not key or not path.is_file():
        return ""
    try:
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, value = line.split("=", 1)
            if env_key.strip() == key:
                return value.strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""


def update_env_values(updates: dict[str, str]) -> None:
    path = api_env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    seen: set[str] = set()
    next_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            next_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            next_lines.append(f"{key}={env_quote(updates[key])}")
            os.environ[key] = str(updates[key] or "")
            seen.add(key)
        else:
            next_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            next_lines.append(f"{key}={env_quote(value)}")
            os.environ[key] = str(value or "")
    path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")
