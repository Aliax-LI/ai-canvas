# Tauri externalBin 占位目录

Batch 1 开发模式通过 `uv run infinite-canvas` 启动 sidecar，**不需要**此目录下的二进制。

生产打包时，运行仓库根目录脚本生成平台二进制：

| 平台 | 命令 |
|------|------|
| macOS / Linux | `./scripts/build-sidecar.sh` |
| Windows | `.\scripts\build-sidecar.ps1` |

产出命名须符合 Tauri 规则，例如：

- `infinite-canvas-x86_64-apple-darwin`
- `infinite-canvas-x86_64-pc-windows-msvc.exe`
- `infinite-canvas-aarch64-apple-darwin`

在 `tauri.conf.json` 中已配置 `"externalBin": ["binaries/infinite-canvas"]`。
