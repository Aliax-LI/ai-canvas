#!/usr/bin/env bash
# Cursor project hook: remind agent to update CONTEXT.md after meaningful code changes.
# Events: stop, subagentStop
# Fail open on errors (always exit 0 unless critical).

set -o pipefail

input=$(cat)
export HOOK_INPUT="$input"

python3 <<'PYEOF'
import json
import os
import subprocess
import sys

MEANINGFUL_PREFIXES = ("services/", "apps/", "tests/", "scripts/", "packages/")
MEANINGFUL_EXACT = frozenset({"pyproject.toml", "package.json"})

FOLLOWUP = (
    "本次会话修改了代码/配置，但 CONTEXT.md §3 尚未更新。"
    "请立即在 CONTEXT.md §3 最上方追加一条更新日志（使用 §4 模板），"
    "包含：变更摘要、影响路径、验证项、下一步、方向对齐。"
    "若里程碑或当前阶段有变化，同步更新 §1。"
)


def emit_empty() -> None:
    print("{}")
    sys.exit(0)


def parse_porcelain_path(line: str) -> str | None:
    if len(line) < 4:
        return None
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip() or None


def is_meaningful(path: str) -> bool:
    if path in MEANINGFUL_EXACT:
        return True
    if path.endswith("/package.json"):
        return True
    return any(path.startswith(prefix) for prefix in MEANINGFUL_PREFIXES)


def is_context_md(path: str) -> bool:
    return path == "CONTEXT.md"


try:
    raw = os.environ.get("HOOK_INPUT", "")
    data = json.loads(raw) if raw.strip() else {}
except (json.JSONDecodeError, TypeError):
    emit_empty()

repo_root = None
for key in ("cwd", "workspace_root", "workspaceRoot", "root", "workspace"):
    value = data.get(key)
    if isinstance(value, str) and os.path.isdir(value):
        repo_root = os.path.abspath(value)
        break
if not repo_root:
    repo_root = os.getcwd()

try:
    git_root = subprocess.run(
        ["git", "-C", repo_root, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if git_root.returncode != 0:
        emit_empty()
    git_root_path = git_root.stdout.strip()
except (OSError, subprocess.TimeoutExpired):
    emit_empty()

try:
    status = subprocess.run(
        ["git", "-C", git_root_path, "status", "--porcelain"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if status.returncode != 0:
        emit_empty()
    lines = [line for line in status.stdout.splitlines() if line.strip()]
except (OSError, subprocess.TimeoutExpired):
    emit_empty()

changed_paths = [p for p in (parse_porcelain_path(line) for line in lines) if p]
has_code_change = any(is_meaningful(path) for path in changed_paths)
has_context_update = any(is_context_md(path) for path in changed_paths)

if has_code_change and not has_context_update:
    print(json.dumps({"followup_message": FOLLOWUP}, ensure_ascii=False))
else:
    print("{}")
PYEOF

exit 0
