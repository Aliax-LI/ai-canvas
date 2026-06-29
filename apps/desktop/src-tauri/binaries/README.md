# Tauri externalBin 目录

生产打包时，运行仓库根目录脚本生成**当前平台**二进制：

| 平台 | 命令 |
|------|------|
| macOS / Linux | `./scripts/build-sidecar.sh` |
| Windows | `.\scripts\build-sidecar.ps1` |

产出命名须符合 Tauri 规则，例如：

- `infinite-canvas-aarch64-apple-darwin`（Apple Silicon，已提交本机构建产物）
- `infinite-canvas-x86_64-apple-darwin`（Intel Mac，需在对应机器构建）
- `infinite-canvas-x86_64-pc-windows-msvc.exe`

在 `tauri.conf.json` 中已配置 `"externalBin": ["binaries/infinite-canvas"]`。

**开发模式**（`pnpm desktop:dev`）不依赖此目录，使用 `uv run infinite-canvas`。

**体积参考**：PyInstaller onefile 约 24MB（aarch64 macOS，2026-06-29）。
