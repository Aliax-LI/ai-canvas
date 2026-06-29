# Infinite Canvas — Tauri 2 桌面端

Tauri 2 壳层：WebView 加载 `apps/web`，Rust 管理 Python sidecar 生命周期。

## 开发

前置：Rust、Node 20+、pnpm 9+、[uv](https://docs.astral.sh/uv/)

```bash
# 仓库根目录
uv sync
pnpm install

# 启动桌面（自动起 Vite + sidecar）
pnpm desktop:dev
# 或
pnpm --filter desktop dev
```

流程：

1. `beforeDevCommand` 启动 `pnpm --filter web dev`（Vite @5173）
2. Rust 在 monorepo 根目录执行 `uv run infinite-canvas --host 127.0.0.1 --port {auto} --data-dir .infinite-canvas-dev`
3. 轮询 `GET /api/app-info` 直至 200（超时 60s）
4. WebView 加载 Vite；注入 `window.__INFINITE_CANVAS_API__`
5. 关窗 / 退出 → kill sidecar 子进程

## 数据目录

| 模式 | 路径 |
|------|------|
| dev | `<repo>/.infinite-canvas-dev` |
| macOS prod | `~/Library/Application Support/infinite-canvas/` |
| Windows prod | `%APPDATA%/infinite-canvas/` |

## 系统托盘

- **显示窗口** — 显示并聚焦主窗口
- **退出** — kill sidecar 后退出应用

## 生产构建（Batch 2+）

1. `./scripts/build-sidecar.sh`（或 Windows `.ps1`）生成 sidecar 二进制
2. `pnpm --filter desktop build`

本批 defer：codesign、notarization、安装包分发。

## 手动验证

- [ ] `pnpm desktop:dev` 窗口正常打开
- [ ] 浏览器外：`curl http://127.0.0.1:{port}/api/app-info` 返回 200
- [ ] 关窗后 `pgrep -f infinite-canvas` 无残留（macOS/Linux）
- [ ] 托盘「退出」同样无残留进程

详见 `docs/superpowers/plans/2026-06-29-m10-tauri-desktop.md`。
