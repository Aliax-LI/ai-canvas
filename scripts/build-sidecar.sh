#!/usr/bin/env bash
# M10 — 将 Python 后端打包为 Tauri sidecar 二进制（占位脚本，Batch 2+ 完善）
#
# 前置：uv、PyInstaller
#   uv pip install pyinstaller
#
# 用法（在仓库根目录）：
#   ./scripts/build-sidecar.sh
#
# 产出：apps/desktop/src-tauri/binaries/infinite-canvas-<target-triple>
# Tauri externalBin 命名规则见：
#   https://v2.tauri.app/develop/sidecar/

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TARGET_TRIPLE="$(rustc -vV | awk '/host:/ { print $2 }')"
OUT_DIR="apps/desktop/src-tauri/binaries"
BINARY_NAME="infinite-canvas-${TARGET_TRIPLE}"

mkdir -p "$OUT_DIR"

echo "==> 同步 Python 依赖"
uv sync

echo "==> PyInstaller 打包 infinite-canvas CLI"
# 入口：services/api/src/infinite_canvas/main.py
uv run pyinstaller \
  --name infinite-canvas \
  --onefile \
  --clean \
  --distpath "$OUT_DIR/dist" \
  --workpath "$OUT_DIR/build" \
  --specpath "$OUT_DIR" \
  --hidden-import infinite_canvas \
  --collect-submodules infinite_canvas \
  services/api/src/infinite_canvas/main.py

mv "$OUT_DIR/dist/infinite-canvas" "$OUT_DIR/$BINARY_NAME"
chmod +x "$OUT_DIR/$BINARY_NAME"

echo "==> 完成: $OUT_DIR/$BINARY_NAME"
echo "下一步: codesign + notarization（macOS）或 Authenticode（Windows）"
