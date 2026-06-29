#!/usr/bin/env bash
# M10 — 将 Python 后端打包为 Tauri sidecar 二进制
#
# 入口与 pyproject [project.scripts] 一致：infinite_canvas.main:main
#
# 用法（在仓库根目录）：
#   ./scripts/build-sidecar.sh
#
# 产出：apps/desktop/src-tauri/binaries/infinite-canvas-<target-triple>

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TARGET_TRIPLE="$(rustc -vV | awk '/host:/ { print $2 }')"
OUT_DIR="apps/desktop/src-tauri/binaries"
BINARY_NAME="infinite-canvas-${TARGET_TRIPLE}"
PYTHONPATH="services/api/src"

mkdir -p "$OUT_DIR"

echo "==> 同步 Python 依赖（含 PyInstaller dev 组）"
uv sync --group dev

echo "==> PyInstaller 打包 infinite-canvas CLI (infinite_canvas.main:main)"
export PYTHONPATH="${PYTHONPATH}:${ROOT}/${PYTHONPATH}"
uv run pyinstaller \
  --name infinite-canvas \
  --onefile \
  --clean \
  --console \
  --paths "${ROOT}/services/api/src" \
  --distpath "${OUT_DIR}/dist" \
  --workpath "${OUT_DIR}/build" \
  --specpath "${OUT_DIR}" \
  --hidden-import infinite_canvas \
  --collect-submodules infinite_canvas \
  --collect-submodules uvicorn \
  --collect-submodules fastapi \
  --collect-submodules starlette \
  --collect-submodules pydantic \
  --copy-metadata infinite-canvas \
  "${ROOT}/scripts/sidecar_entry.py"

mv "${OUT_DIR}/dist/infinite-canvas" "${OUT_DIR}/${BINARY_NAME}"
chmod +x "${OUT_DIR}/${BINARY_NAME}"

rm -rf "${OUT_DIR}/dist" "${OUT_DIR}/build" "${OUT_DIR}/infinite-canvas.spec"

echo "==> 完成: ${OUT_DIR}/${BINARY_NAME} ($(du -h "${OUT_DIR}/${BINARY_NAME}" | awk '{print $1}'))"
echo "下一步: codesign + notarization（macOS）或 Authenticode（Windows）"
